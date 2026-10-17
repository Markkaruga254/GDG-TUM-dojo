import { useQuery } from "@tanstack/react-query";

import { fetchMe } from "@/api/auth";
import { qk } from "@/lib/query-keys";

/**
 * Session query. `data` is `null` when signed out — 401 is a normal state,
 * not an error — so components can branch on `isAuthenticated` directly.
 */
export function useMe() {
  return useQuery({
    queryKey: qk.me,
    queryFn: ({ signal }) => fetchMe(signal),
    retry: false,
    staleTime: 30_000,
  });
}

export interface Session {
  user: Awaited<ReturnType<typeof fetchMe>>;
  isLoading: boolean;
  isAuthenticated: boolean;
  isStaff: boolean;
  isAdmin: boolean;
}

export function useSession(): Session {
  const query = useMe();
  const user = query.data ?? null;
  return {
    user,
    isLoading: query.isLoading,
    isAuthenticated: user !== null,
    isStaff: user?.role === "admin" || user?.role === "moderator",
    isAdmin: user?.role === "admin",
  };
}
