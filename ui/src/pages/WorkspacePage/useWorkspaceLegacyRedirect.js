import { useEffect } from "react";

import { legacyWorkspaceTabRedirectTarget } from "../../components/work/traceability/traceabilityState.js";

export function useWorkspaceLegacyRedirect(searchParams, navigate) {
  useEffect(() => {
    const target = legacyWorkspaceTabRedirectTarget(searchParams);
    if (target) navigate(target, { replace: true });
  }, [navigate, searchParams]);
}
