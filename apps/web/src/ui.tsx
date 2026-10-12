import { useEffect, useId, useRef, type ReactNode } from "react";
import { WarningCircle, X } from "@phosphor-icons/react";
import { ApiError } from "./api";

export function ErrorNotice({ error }: { error: unknown }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (error) ref.current?.focus();
  }, [error]);
  if (!error) return null;
  const labels: Record<string, string> = {
    email: "ایمیل",
    password: "رمز ورود",
    workspace_name: "نام فروشگاه",
    accepted_policy: "پذیرش شرایط",
  };
  const fields =
    error instanceof ApiError
      ? error.fields.filter(
          (f) => labels[f.field] && document.getElementById(f.field),
        )
      : [];
  return (
    <div ref={ref} tabIndex={-1} role="alert" className="alert error">
      <WarningCircle aria-hidden="true" size={20} />
      <div>
        {error instanceof Error ? error.message : String(error)}
        {fields.length > 0 && (
          <ul>
            {fields.map((f) => (
              <li key={f.field}>
                <a
                  href={`#${f.field}`}
                  onClick={() => document.getElementById(f.field)?.focus()}
                >
                  بررسی {labels[f.field]}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
export function Success({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="alert success">
      {children}
    </p>
  );
}
export function Modal({
  open,
  title,
  close,
  children,
}: {
  open: boolean;
  title: string;
  close: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const node = ref.current;
    if (open && !node?.open) node?.showModal();
    if (!open && node?.open) node.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClose={close}
      aria-labelledby={titleId}
    >
      <div className="dialog-header">
        <h2 id={titleId}>{title}</h2>
        <button
          type="button"
          aria-label="بستن"
          className="icon-button"
          onClick={close}
        >
          <X size={22} aria-hidden="true" />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export const stateText = {
  low: "کمبود",
  normal: "موجودی مناسب",
  high: "موجودی زیاد",
};
export const productionText: Record<string, string> = {
  none: "بررسی نشده",
  planned: "در صف تأمین",
  producing: "در حال تولید",
};
