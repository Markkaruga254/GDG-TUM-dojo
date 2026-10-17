import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      className="ba-toaster"
      position="bottom-right"
      gap={10}
      toastOptions={{
        classNames: {
          toast: "!rounded-xl",
          description: "!text-muted",
          actionButton: "!bg-primary !text-primary-fg !rounded-md",
          cancelButton: "!bg-surface-2 !text-ink !rounded-md",
        },
      }}
    />
  );
}
