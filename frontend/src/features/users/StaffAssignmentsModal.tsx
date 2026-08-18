import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { School, GraduationCap, X, Plus, Star } from "lucide-react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { apiErrorMessage } from "@/api/client";
import { departmentsApi, classesApi, staffAssignmentsApi } from "@/api/organization";
import type { UserOut } from "@/types/user";

interface StaffAssignmentsModalProps {
  staff: UserOut;
  open: boolean;
  onClose: () => void;
}

export function StaffAssignmentsModal({ staff, open, onClose }: StaffAssignmentsModalProps) {
  const queryClient = useQueryClient();
  const [selectedDept, setSelectedDept] = useState("");
  const [selectedClass, setSelectedClass] = useState("");

  const { data: assignedDepts = [], isLoading: loadingDepts } = useQuery({
    queryKey: ["staff-departments", staff.id],
    queryFn: () => staffAssignmentsApi.listDepartments(staff.id),
    enabled: open,
  });

  const { data: assignedClasses = [], isLoading: loadingClasses } = useQuery({
    queryKey: ["staff-classes", staff.id],
    queryFn: () => staffAssignmentsApi.listClasses(staff.id),
    enabled: open,
  });

  const { data: allDepartments = [] } = useQuery({
    queryKey: ["departments", staff.college_id],
    queryFn: () => departmentsApi.list({ college_id: staff.college_id ?? undefined }),
    enabled: open,
  });

  const { data: allClasses = [] } = useQuery({
    queryKey: ["classes", staff.college_id],
    queryFn: () => classesApi.list({ college_id: staff.college_id ?? undefined }),
    enabled: open,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["staff-departments", staff.id] });
    queryClient.invalidateQueries({ queryKey: ["staff-classes", staff.id] });
  };

  const assignDept = useMutation({
    mutationFn: (department_id: number) => staffAssignmentsApi.assignDepartment(staff.id, { department_id }),
    onSuccess: () => {
      toast.success("Department assigned");
      setSelectedDept("");
      invalidate();
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not assign department")),
  });

  const unassignDept = useMutation({
    mutationFn: (departmentId: number) => staffAssignmentsApi.unassignDepartment(staff.id, departmentId),
    onSuccess: invalidate,
    onError: (err) => toast.error(apiErrorMessage(err)),
  });

  const assignClass = useMutation({
    mutationFn: (class_id: number) => staffAssignmentsApi.assignClass(staff.id, { class_id }),
    onSuccess: () => {
      toast.success("Class assigned");
      setSelectedClass("");
      invalidate();
    },
    onError: (err) => toast.error(apiErrorMessage(err, "Could not assign class")),
  });

  const unassignClass = useMutation({
    mutationFn: (classId: number) => staffAssignmentsApi.unassignClass(staff.id, classId),
    onSuccess: invalidate,
    onError: (err) => toast.error(apiErrorMessage(err)),
  });

  const toggleIncharge = useMutation({
    mutationFn: ({ classId, is_incharge }: { classId: number; is_incharge: boolean }) =>
      staffAssignmentsApi.updateClass(staff.id, classId, { is_incharge }),
    onSuccess: invalidate,
    onError: (err) => toast.error(apiErrorMessage(err)),
  });

  const availableDepts = allDepartments.filter(
    (d) => !assignedDepts.some((a) => a.department_id === d.id && a.is_active),
  );
  const availableClasses = allClasses.filter(
    (c) => !assignedClasses.some((a) => a.class_id === c.id),
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Assignments — ${staff.profile?.name || staff.username}`}
      description="Control which departments and classes this staff member can access."
      size="lg"
    >
      <div className="space-y-6">
        {/* Departments */}
        <section>
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-200">
            <School className="size-4 text-brand-400" /> Departments
          </h4>
          {loadingDepts ? (
            <Spinner size={20} />
          ) : (
            <div className="mb-3 flex flex-wrap gap-2">
              {assignedDepts.filter((d) => d.is_active).length === 0 && (
                <p className="text-xs text-slate-500">No departments assigned yet.</p>
              )}
              {assignedDepts
                .filter((d) => d.is_active)
                .map((d) => (
                  <Badge key={d.id} variant="brand" className="gap-1.5 pr-1.5">
                    {d.department_name}
                    <button
                      onClick={() => unassignDept.mutate(d.department_id)}
                      className="rounded-full p-0.5 hover:bg-white/20"
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                ))}
            </div>
          )}
          <div className="flex gap-2">
            <Select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              placeholder="Select a department to add"
              options={availableDepts.map((d) => ({ value: String(d.id), label: d.name }))}
              className="flex-1"
            />
            <Button
              type="button"
              size="md"
              variant="glass"
              disabled={!selectedDept}
              loading={assignDept.isPending}
              onClick={() => selectedDept && assignDept.mutate(Number(selectedDept))}
            >
              <Plus className="size-4" />
            </Button>
          </div>
        </section>

        {/* Classes */}
        <section>
          <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-200">
            <GraduationCap className="size-4 text-accent-400" /> Classes
          </h4>
          {loadingClasses ? (
            <Spinner size={20} />
          ) : (
            <div className="mb-3 space-y-2">
              {assignedClasses.length === 0 && (
                <p className="text-xs text-slate-500">No classes assigned yet.</p>
              )}
              {assignedClasses.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"
                >
                  <span className="text-sm text-slate-200">{c.class_name}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        toggleIncharge.mutate({ classId: c.class_id, is_incharge: !c.is_incharge })
                      }
                      className="flex items-center gap-1"
                      title="Toggle class in-charge"
                    >
                      <Star
                        className={
                          c.is_incharge
                            ? "size-4 fill-warning-500 text-warning-500"
                            : "size-4 text-slate-600"
                        }
                      />
                    </button>
                    <button
                      onClick={() => unassignClass.mutate(c.class_id)}
                      className="rounded-lg p-1 text-slate-500 hover:bg-danger-500/10 hover:text-danger-500"
                    >
                      <X className="size-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <Select
              value={selectedClass}
              onChange={(e) => setSelectedClass(e.target.value)}
              placeholder="Select a class to add"
              options={availableClasses.map((c) => ({ value: String(c.id), label: c.name }))}
              className="flex-1"
            />
            <Button
              type="button"
              size="md"
              variant="glass"
              disabled={!selectedClass}
              loading={assignClass.isPending}
              onClick={() => selectedClass && assignClass.mutate(Number(selectedClass))}
            >
              <Plus className="size-4" />
            </Button>
          </div>
        </section>
      </div>
    </Modal>
  );
}
