import { GitHubIcon } from "@/components/common/github-icon";

import { githubLoginUrl } from "@/api/auth";
import { buttonClasses, type ButtonClassOptions } from "@/components/ui/button";

export interface SignInButtonProps extends Omit<ButtonClassOptions, "variant"> {
  label?: string;
}

/** Starts the GitHub OAuth flow with a full-page navigation. */
export function SignInButton({
  label = "Sign in with GitHub",
  size = "md",
  className,
}: SignInButtonProps) {
  return (
    <a href={githubLoginUrl()} className={buttonClasses({ size, className })}>
      <GitHubIcon aria-hidden />
      {label}
    </a>
  );
}
