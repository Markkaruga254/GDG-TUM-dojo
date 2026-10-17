import { LogoMark } from "@/components/common/logo";

export function Footer() {
  return (
    <footer className="mt-20 border-t border-line py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-4 px-4 text-sm text-muted sm:flex-row sm:px-6 lg:px-8">
        <div className="flex items-center gap-2.5">
          <LogoMark className="size-5" />
          <span>
            <span className="font-medium text-ink">Build Arena</span> · GDG TUM
          </span>
        </div>
        <p className="text-center text-xs text-faint">
          Ship real projects. Get scored by automated evaluation. Climb the board.
        </p>
      </div>
    </footer>
  );
}
