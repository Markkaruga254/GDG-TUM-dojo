import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, LayoutDashboard, LogOut, Settings, User as UserIcon } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";

import { logout } from "@/api/auth";
import { Avatar } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { UserSelf } from "@/api/types";
import { qk } from "@/lib/query-keys";
import { displayNameOf } from "@/lib/utils";

export interface UserMenuProps {
  user: UserSelf;
  isStaff: boolean;
}

export function UserMenu({ user, isStaff }: UserMenuProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const signOut = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(qk.me, null);
      queryClient.clear();
      toast.success("Signed out.");
      navigate("/");
    },
    onError: () => {
      queryClient.setQueryData(qk.me, null);
      queryClient.clear();
      navigate("/");
    },
  });

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="ml-1 rounded-full transition-opacity hover:opacity-85 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ba-ring)"
        aria-label="Account menu"
      >
        <Avatar user={user} size="sm" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel className="normal-case">
          <span className="block truncate text-sm font-semibold text-ink">
            {displayNameOf(user)}
          </span>
          <span className="block truncate text-xs font-normal text-faint">
            @{user.github_username}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to={`/u/${user.github_username}`}>
            <UserIcon aria-hidden />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/submissions">
            <BookOpen aria-hidden />
            My submissions
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/settings">
            <Settings aria-hidden />
            Settings
          </Link>
        </DropdownMenuItem>
        {isStaff ? (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/staff">
                <LayoutDashboard aria-hidden />
                Staff console
              </Link>
            </DropdownMenuItem>
          </>
        ) : null}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="text-danger [&_svg]:text-danger"
          onSelect={(event) => {
            event.preventDefault();
            signOut.mutate();
          }}
        >
          <LogOut aria-hidden />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
