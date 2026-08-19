import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, FileUp, RotateCcw, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { documentsApi } from "@/api/documents";
import { apiErrorMessage } from "@/api/client";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import type { BadgeProps } from "@/components/ui/Badge";
import { DOC_TYPE_LABELS, REQUIRED_DOC_TYPES } from "@/types/document";
import type { DocType, StudentDocumentOut } from "@/types/document";

const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  pending: "warning",
  verified: "success",
  rejected: "danger",
};

const STATUS_ICON = {
  pending: Clock,
  verified: CheckCircle2,
  rejected: XCircle,
};

/** True once every doc in REQUIRED_DOC_TYPES has been uploaded (any status —
 * "pending" still counts as submitted; admin review happens separately).
 * ApplyEntrancePage gates registration on this. */
export function hasRequiredDocuments(docs: StudentDocumentOut[]): boolean {
  const uploaded = new Set(docs.map((d) => d.doc_type));
  return REQUIRED_DOC_TYPES.every((t) => uploaded.has(t));
}

/**
 * Lets an applicant upload the documents required to register for an
 * entrance exam (10th/12th marksheet, age proof) plus optional extras
 * (diploma marksheet, photo). Re-uploading a doc type replaces the file and
 * resets it to "pending" — see routers/documents.py::upload_document.
 */
// Only marksheets carry a board/place-stated — age proof and photo don't.
const BOARD_FIELD_TYPES: DocType[] = ["tenth_marksheet", "twelfth_marksheet", "diploma_marksheet"];

export function DocumentUploadSection() {
  const qc = useQueryClient();
  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["my-documents"],
    queryFn: documentsApi.myDocuments,
  });
  const [uploadingType, setUploadingType] = useState<DocType | null>(null);
  // Draft board/place text per doc type, keyed while the file picker hasn't
  // fired yet — pre-filled from the existing document (if any) so editing
  // just the board doesn't require re-uploading the file.
  const [boardDraft, setBoardDraft] = useState<Record<string, string>>({});
  const [placeDraft, setPlaceDraft] = useState<Record<string, string>>({});

  const upload = useMutation({
    mutationFn: (params: { doc_type: DocType; file: File; issuing_board?: string; issued_place?: string }) =>
      documentsApi.upload(params),
    onMutate: (params) => setUploadingType(params.doc_type),
    onSuccess: () => {
      toast.success("Document uploaded");
      qc.invalidateQueries({ queryKey: ["my-documents"] });
    },
    onError: (e) => toast.error(apiErrorMessage(e, "Could not upload this document")),
    onSettled: () => setUploadingType(null),
  });

  const docByType = new Map(documents.map((d) => [d.doc_type, d]));
  const allTypes: DocType[] = ["tenth_marksheet", "twelfth_marksheet", "age_proof", "diploma_marksheet", "photo"];

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {allTypes.map((docType) => {
        const doc = docByType.get(docType);
        const required = REQUIRED_DOC_TYPES.includes(docType);
        const StatusIcon = doc ? STATUS_ICON[doc.status] : null;
        const busy = uploadingType === docType;
        const needsBoard = BOARD_FIELD_TYPES.includes(docType);
        const board = boardDraft[docType] ?? doc?.issuing_board ?? "";
        const place = placeDraft[docType] ?? doc?.issued_place ?? "";

        return (
          <Card key={docType} className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 font-medium text-slate-100">
                  {DOC_TYPE_LABELS[docType]}
                  {required && <span className="text-danger-400">*</span>}
                </p>
                {doc ? (
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant={STATUS_VARIANT[doc.status]} dot>
                      {StatusIcon && <StatusIcon className="mr-1 size-3" />}
                      {doc.status}
                    </Badge>
                    {doc.status === "rejected" && doc.remarks && (
                      <span className="truncate text-xs text-danger-400" title={doc.remarks}>
                        {doc.remarks}
                      </span>
                    )}
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-slate-500">{required ? "Required" : "Optional"} — not uploaded</p>
                )}
              </div>

              <label
                className="flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg border border-dashed border-white/15 px-3 py-2 text-xs text-slate-400 hover:border-brand-400 hover:text-brand-300"
                title={doc ? "Replace file" : "Upload file"}
              >
                {busy ? (
                  "Uploading…"
                ) : doc ? (
                  <>
                    <RotateCcw className="size-3.5" /> Replace
                  </>
                ) : (
                  <>
                    <FileUp className="size-3.5" /> Upload
                  </>
                )}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,application/pdf"
                  className="hidden"
                  disabled={busy}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      upload.mutate({
                        doc_type: docType,
                        file,
                        issuing_board: needsBoard ? board.trim() || undefined : undefined,
                        issued_place: needsBoard ? place.trim() || undefined : undefined,
                      });
                    }
                    e.target.value = "";
                  }}
                />
              </label>
            </div>

            {needsBoard && (
              <div className="grid grid-cols-2 gap-2">
                <Input
                  placeholder="Board (e.g. State Board, CBSE)"
                  value={board}
                  disabled={busy}
                  onChange={(e) => setBoardDraft((d) => ({ ...d, [docType]: e.target.value }))}
                  className="text-xs"
                />
                <Input
                  placeholder="State/place where studied"
                  value={place}
                  disabled={busy}
                  onChange={(e) => setPlaceDraft((d) => ({ ...d, [docType]: e.target.value }))}
                  className="text-xs"
                />
              </div>
            )}
          </Card>
        );
      })}
      {isLoading && <p className="text-sm text-slate-500">Loading your documents…</p>}
    </div>
  );
}
