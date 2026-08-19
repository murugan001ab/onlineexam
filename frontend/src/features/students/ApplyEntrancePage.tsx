import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, FileSpreadsheet, Users, Wallet } from "lucide-react";
import toast from "react-hot-toast";
import { entranceApi } from "@/api/entrance";
import { documentsApi } from "@/api/documents";
import { apiErrorMessage } from "@/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { cn, formatCurrency, formatDateTime } from "@/lib/utils";
import { DocumentUploadSection, hasRequiredDocuments } from "@/features/students/DocumentUploadSection";

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export function ApplyEntrancePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [selectedExam, setSelectedExam] = useState<number | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [heldSlot, setHeldSlot] = useState<number | null>(null);
  const [heldId, setHeldId] = useState<number | null>(null);
  const [registrationId, setRegistrationId] = useState<number | null>(null);

  const { data: exams = [], isLoading: loadingExams } = useQuery({
    queryKey: ["entrance-open-exams"],
    queryFn: entranceApi.listOpenExams,
  });
  const { data: slots = [], isLoading: loadingSlots } = useQuery({
    queryKey: ["entrance-slots", selectedExam],
    queryFn: () => entranceApi.listSlots(selectedExam!),
    enabled: !!selectedExam,
  });
  const { data: myDocuments = [] } = useQuery({
    queryKey: ["my-documents"],
    queryFn: documentsApi.myDocuments,
  });
  const documentsReady = hasRequiredDocuments(myDocuments);

  const holdMutation = useMutation({
    mutationFn: (slotId: number) => entranceApi.holdSlot(slotId),
    onSuccess: (res, slotId) => {
      setHeldSlot(slotId);
      setHeldId(res.id);
      toast.success("Slot held for you — complete registration to confirm it");
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not hold that slot — it may be full")),
  });

  const registerMutation = useMutation({
    mutationFn: () => entranceApi.register({ exam_id: selectedExam!, hold_id: heldId! }),
    onSuccess: (reg) => {
      qc.invalidateQueries({ queryKey: ["my-entrance-registrations"] });
      // Free exams (fee <= 0) are auto-confirmed by the backend at
      // registration time — there's no payment to collect, so skip straight
      // past the payment card instead of showing a "Pay" button that would
      // 400 ("registration does not have a pending payment").
      if (reg.status === "confirmed") {
        toast.success("Application confirmed!");
        navigate("/entrance");
        return;
      }
      setRegistrationId(reg.id);
      toast.success("Application created — proceed to payment");
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not create application")),
  });

  const payMutation = useMutation({
    mutationFn: async () => {
      if (!registrationId) throw new Error("No application yet");
      const order = await entranceApi.createPaymentOrder(registrationId);

      // Local/dev deployments without Razorpay credentials get key_id: null
      // back (see backend utils/payments.is_live()) — there's no real
      // checkout widget to open, so confirm the mock payment directly
      // instead of handing a null key to the Razorpay JS SDK.
      if (!order.key_id) {
        await entranceApi.mockConfirmPayment(registrationId);
        return;
      }

      const ok = await loadRazorpayScript();
      if (!ok || !window.Razorpay) throw new Error("Could not load payment gateway");
      return new Promise<void>((resolve, reject) => {
        const rz = new window.Razorpay!({
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          order_id: order.order_id,
          name: "Entrance Exam Application Fee",
          handler: async (response: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => {
            try {
              await entranceApi.verifyPayment({
                registration_id: registrationId,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              });
              resolve();
            } catch (err) {
              reject(err);
            }
          },
          modal: { ondismiss: () => reject(new Error("Payment cancelled")) },
          theme: { color: "#8b5cf6" },
        });
        rz.open();
      });
    },
    onSuccess: () => {
      toast.success("Payment verified — application confirmed!");
      qc.invalidateQueries({ queryKey: ["my-entrance-registrations"] });
      navigate("/entrance");
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Payment could not be completed")),
  });

  const exam = exams.find((e) => e.id === selectedExam);

  return (
    <div>
      <PageHeader title="Apply for Entrance Exam" description="Choose an exam, pick a slot, and complete payment to confirm your application." />

      {!registrationId && (
        <>
          <section className="mb-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-300">1. Choose an exam</h3>
            {loadingExams ? (
              <Spinner size={22} />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {exams.map((e) => (
                  <Card
                    key={e.id}
                    className={cn("cursor-pointer", selectedExam === e.id && "ring-2 ring-brand-400")}
                    onClick={() => { setSelectedExam(e.id); setSelectedSlot(null); setHeldSlot(null); }}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex size-9 items-center justify-center rounded-lg bg-brand-500/15 text-brand-300"><FileSpreadsheet className="size-4" /></div>
                      <div>
                        <CardTitle>{e.name}</CardTitle>
                        <p className="text-xs text-slate-500">{e.exam_type_name ?? "Entrance"}</p>
                      </div>
                    </div>
                    <p className="mt-3 flex items-center gap-2 text-xs text-slate-400"><Wallet className="size-3.5" /> {formatCurrency(e.fee, e.fee_currency)}</p>
                  </Card>
                ))}
                {exams.length === 0 && <Card><CardTitle>No open exams</CardTitle><p className="mt-2 text-sm text-slate-400">Check back later — your college hasn&apos;t opened any entrance exam applications yet.</p></Card>}
              </div>
            )}
          </section>

          {selectedExam && (
            <section className="mb-6">
              <h3 className="mb-3 text-sm font-semibold text-slate-300">2. Upload your documents</h3>
              <p className="mb-3 text-xs text-slate-500">Required: 10th marksheet, 12th marksheet, and age proof. These are matched against your application, not this specific exam, so you only need to upload them once.</p>
              <DocumentUploadSection />
            </section>
          )}

          {selectedExam && (
            <section className="mb-6">
              <h3 className="mb-3 text-sm font-semibold text-slate-300">3. Pick a slot</h3>
              {loadingSlots ? (
                <Spinner size={22} />
              ) : (
                <div className="grid gap-3 md:grid-cols-3">
                  {slots.map((s) => (
                    <Card
                      key={s.id}
                      className={cn("cursor-pointer", selectedSlot === s.id && "ring-2 ring-brand-400", s.available <= 0 && "pointer-events-none opacity-40")}
                      onClick={() => { setSelectedSlot(s.id); holdMutation.mutate(s.id); }}
                    >
                      <p className="font-medium text-slate-100">{s.name ?? `Slot #${s.id}`}</p>
                      <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-400"><CalendarClock className="size-3.5" /> {formatDateTime(s.starts_at)}</p>
                      <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500"><Users className="size-3.5" /> {s.available} of {s.max_capacity} available</p>
                      {heldSlot === s.id && <Badge variant="success" className="mt-2" dot>Held for you</Badge>}
                    </Card>
                  ))}
                  {slots.length === 0 && <Card><CardTitle>No slots open</CardTitle><p className="mt-2 text-sm text-slate-400">No exam slots are currently open for booking.</p></Card>}
                </div>
              )}
            </section>
          )}

          {selectedExam && (
            <>
              {!documentsReady && (
                <p className="mb-3 text-xs text-warning-400">Upload your 10th marksheet, 12th marksheet, and age proof above before continuing.</p>
              )}
              <Button
                size="lg"
                disabled={!selectedExam || !heldId || !documentsReady || registerMutation.isPending}
                loading={registerMutation.isPending}
                onClick={() => registerMutation.mutate()}
              >
                Continue to Application
              </Button>
            </>
          )}
        </>
      )}

      {registrationId && (
        <Card className="max-w-md">
          <CardTitle>Application created</CardTitle>
          <p className="mt-2 text-sm text-slate-400">
            {exam ? `Fee for ${exam.name}: ${formatCurrency(exam.fee, exam.fee_currency)}` : "Complete payment to confirm your seat."}
          </p>
          <Button className="mt-4 w-full" loading={payMutation.isPending} onClick={() => payMutation.mutate()}>
            <Wallet className="size-4" /> Pay & Confirm Application
          </Button>
        </Card>
      )}
    </div>
  );
}
