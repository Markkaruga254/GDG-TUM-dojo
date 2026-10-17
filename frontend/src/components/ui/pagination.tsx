import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";

import { Button } from "./button";

export interface PaginationProps {
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

function buildPageItems(page: number, pages: number): Array<number | "ellipsis"> {
  if (pages <= 7) return Array.from({ length: pages }, (_, index) => index + 1);
  const items: Array<number | "ellipsis"> = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(pages - 1, page + 1);
  if (start > 2) items.push("ellipsis");
  for (let current = start; current <= end; current += 1) items.push(current);
  if (end < pages - 1) items.push("ellipsis");
  items.push(pages);
  return items;
}

export function Pagination({ page, pages, onPageChange, className }: PaginationProps) {
  if (pages <= 1) return null;
  const items = buildPageItems(page, pages);

  return (
    <nav
      className={cn("flex items-center justify-center gap-1", className)}
      aria-label="Pagination"
    >
      <Button
        variant="ghost"
        size="icon-sm"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="Previous page"
      >
        <ChevronLeft aria-hidden />
      </Button>
      {items.map((item, index) =>
        item === "ellipsis" ? (
          <span
            key={`ellipsis-${index}`}
            className="flex size-7.5 items-center justify-center text-faint"
          >
            <MoreHorizontal className="size-3.5" aria-hidden />
          </span>
        ) : (
          <Button
            key={item}
            variant={item === page ? "primary" : "ghost"}
            size="icon-sm"
            onClick={() => onPageChange(item)}
            aria-label={`Page ${item}`}
            aria-current={item === page ? "page" : undefined}
          >
            {item}
          </Button>
        ),
      )}
      <Button
        variant="ghost"
        size="icon-sm"
        disabled={page >= pages}
        onClick={() => onPageChange(page + 1)}
        aria-label="Next page"
      >
        <ChevronRight aria-hidden />
      </Button>
    </nav>
  );
}
