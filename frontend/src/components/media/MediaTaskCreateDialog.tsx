import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";


type MediaTaskCreateDialogProps = {
  open: boolean;
  title: string;
  description: string;
  busy?: boolean;
  onClose: () => void;
  children: ReactNode;
};


export function MediaTaskCreateDialog({
  open,
  title,
  description,
  busy = false,
  onClose,
  children,
}: MediaTaskCreateDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const reactId = useId();
  const titleId = `media-create-title-${reactId}`;
  const descriptionId = `media-create-description-${reactId}`;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      // 记录触发按钮；弹窗关闭后把键盘焦点交还给原位置。
      returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      dialog.showModal();
      // 显式聚焦业务表单的首要字段；浏览器默认往往会先聚焦右上角关闭按钮。
      dialog.querySelector<HTMLElement>("[data-dialog-initial-focus]")?.focus();
      document.body.classList.add("has-media-dialog");
      return;
    }

    if (!open && dialog.open) {
      dialog.close();
      document.body.classList.remove("has-media-dialog");
      returnFocusRef.current?.focus();
    }
  }, [open]);

  useEffect(() => () => {
    document.body.classList.remove("has-media-dialog");
    if (dialogRef.current?.open) dialogRef.current.close();
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      if (!busy) onClose();
    };
    // 使用捕获阶段兜底不同浏览器对原生 dialog cancel 事件的实现差异。
    document.addEventListener("keydown", closeOnEscape, true);
    return () => document.removeEventListener("keydown", closeOnEscape, true);
  }, [busy, onClose, open]);

  function requestClose() {
    // 上传或提交过程中保持弹窗稳定，避免用户误关后误以为任务没有创建。
    if (!busy) onClose();
  }

  return (
    <dialog
      ref={dialogRef}
      className="media-create-dialog"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault();
        requestClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) requestClose();
      }}
    >
      <div className="media-create-dialog-card">
        <header className="media-create-dialog-header">
          <div>
            <p>创建任务</p>
            <h2 id={titleId}>{title}</h2>
            <span id={descriptionId}>{description}</span>
          </div>
          <button type="button" aria-label="关闭创建任务弹窗" disabled={busy} onClick={requestClose}>
            <X aria-hidden />
          </button>
        </header>
        <div className="media-create-dialog-body">{children}</div>
      </div>
    </dialog>
  );
}
