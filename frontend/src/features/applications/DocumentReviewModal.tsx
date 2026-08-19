import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ExternalLink, FileText, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { documentsApi } from "@/api/documents";
import { apiErrorMessage } from "@/api/client";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { Textarea } from "@/components/ui/Textarea";
import { DOC_TYPE_LABELS } from "@/types/document";
import type { StudentDocumentOut } from "@/types/document";

const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  pending: "warning",
  verified: "success",
  rejected: "danger",
};

/**
 * Admin/staff view of one applicant's uploaded documents (10th/12th
 * marksheet, age proof, etc.) — approve or reject each with an optional
 * remark. Backed by GET/PATCH /admin/students/{id}/documents.
 */
export function DocumentReviewModal({
  studentId,
  open,
  onClose,
}: {
  studentId: number | null;
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["student-documents", studentId],
    queryFn: () => documentsApi.listForStudent(studentId!),
    enabled: open && studentId != null,
  });

  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [remarks, setRemarks] = useState("");

  const review = useMutation({
    mutationFn: (params: { documentId: number; status: "verified" | "rejected"; remarks?: string | null }) =>
      documentsApi.review(studentId!, params.documentId, { status: params.status, remarks: params.remarks }),
    onSuccess: () => {
      toast.success("Document reviewed");
      qc.invalidateQueries({ queryKey: ["student-documents", studentId] });
      setRejectingId(null);
      setRemarks("");
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not update this document")),
  });

  function approve(doc: StudentDocumentOut) {
    review.mutate({ documentId: doc.id, status: "verified" });
  }

  function confirmReject(doc: StudentDocumentOut) {
    review.mutate({ documentId: doc.id, status: "rejected", remarks: remarks.trim() || null });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Review documents"
      description="Verify or reject each uploaded proof document."
      size="lg"
    >
      {isLoading && (
        <div className="flex justify-center py-10">
          <Spinner size={24} />
        </div>
      )}

      {!isLoading && documents.length === 0 && (
        <p className="py-6 text-center text-sm text-slate-500">This applicant hasn&apos;t uploaded any documents yet.</p>
      )}

      <div className="space-y-3">
        {documents.map((doc) => (
          <div key={doc.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <FileText className="mt-0.5 size-4 shrink-0 text-brand-300" />
                <div>
                  <p className="font-medium text-slate-100">{DOC_TYPE_LABELS[doc.doc_type]}</p>
                  <a
                    href={doc.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-0.5 flex items-center gap-1 text-xs text-brand-300 hover:text-brand-200"
                  >
                    {doc.original_filename ?? "View file"} <ExternalLink className="size-3" />
                  </a>
                  {(doc.issuing_board || doc.issued_place) && (
                    <p className="mt-1 text-xs text-slate-500">
                      {doc.issuing_board && <>Board: {doc.issuing_board}</>}
                      {doc.issuing_board && doc.issued_place && " \u00b7 "}
                      {doc.issued_place && <>Stated at: {doc.issued_place}</>}
                    </p>
                  )}
                  {doc.status === "rejected" && doc.remarks && (
                    <p className="mt-1 text-xs text-danger-400">Rejected: {doc.remarks}</p>
                  )}
                </div>
              </div>
              <Badge variant={STATUS_VARIANT[doc.status]} dot>
                {doc.status}
              </Badge>
            </div>

            {doc.status === "pending" && rejectingId !== doc.id && (
              <div className="mt-3 flex gap-2">
                <Button size="sm" disabled={review.isPending} onClick={() => approve(doc)}>
                  <CheckCircle2 className="size-3.5" /> Verify
                </Button>
                <Button
                  size="sm"
                  variant="glass"
                  disabled={review.isPending}
                  onClick={() => {
                    setRejectingId(doc.id);
                    setRemarks("");
                  }}
                >
                  <XCircle className="size-3.5" /> Reject
                </Button>
              </div>
            )}

            {rejectingId === doc.id && (
              <div className="mt-3 space-y-2">
                <Textarea
                  rows={2}
                  placeholder="Reason for rejection (shown to the applicant)"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="danger"
                    loading={review.isPending}
                    onClick={() => confirmReject(doc)}
                  >
                    Confirm reject
                  </Button>
                  <Button size="sm" variant="glass" onClick={() => setRejectingId(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {doc.status !== "pending" && rejectingId !== doc.id && (
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  variant="glass"
                  disabled={review.isPending}
                  onClick={() => (doc.status === "verified" ? setRejectingId(doc.id) : approve(doc))}
                >
                  {doc.status === "verified" ? (
                    <>
                      <XCircle className="size-3.5" /> Change to rejected
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="size-3.5" /> Change to verified
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </Modal>
  );
}
