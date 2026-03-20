import "server-only";

import { NextRequest, NextResponse } from "next/server";

import { BackendApiError, meWithBackend, refreshWithBackend } from "@/features/auth/api/server-auth";
import {
  ACCESS_COOKIE_NAME,
  clearSessionCookies,
  REFRESH_COOKIE_NAME,
  setActiveWorkspaceCookie,
  setSessionCookies,
  WORKSPACE_COOKIE_NAME
} from "@/features/auth/api/session-cookies";
import { resolveForwardedFor } from "@/shared/security/forwarded-for";
import type { AuthSession, BackendRefreshResponse } from "@/features/auth/types/auth-types";
import type { WorkspaceRole } from "@/features/rbac/types/rbac-types";
import { PlanAccessDeniedError } from "@/shared/errors/plan-access-denied-error";
import { PlanLimitExceededError } from "@/shared/errors/plan-limit-exceeded-error";
import { RbacForbiddenError } from "@/shared/errors/rbac-forbidden-error";
import { WorkspaceScopeError } from "@/shared/errors/workspace-scope-error";

type SessionSuccess<T> = {
  data: T;
  refreshedTokens?: BackendRefreshResponse;
  workspaceId?: string;
};

export type WorkspaceContext = {
  accessToken: string;
  workspaceId: string;
  userId: string;
  role: WorkspaceRole;
  session: AuthSession;
  forwardedFor?: string;
};

function unauthorizedResponse(): NextResponse {
  const response = NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  clearSessionCookies(response);
  return response;
}

function forbiddenWorkspaceResponse(details?: { expectedWorkspaceId: string; actualWorkspaceId: string | null }): NextResponse {
  return NextResponse.json(
    {
      message: "Forbidden workspace context",
      ...(details
        ? {
            details
          }
        : {})
    },
    { status: 403 }
  );
}

function forbiddenRoleResponse(error: RbacForbiddenError): NextResponse {
  return NextResponse.json(
    {
      code: "permission_denied",
      message: "Permission denied",
      details: {
        action: error.action,
        role: error.role
      }
    },
    { status: 403 }
  );
}

function planLimitExceededResponse(error: PlanLimitExceededError): NextResponse {
  return NextResponse.json(
    {
      code: "plan_limit_exceeded",
      message: error.message,
      limitType: error.limitType
    },
    { status: error.status }
  );
}

function planAccessDeniedResponse(error: PlanAccessDeniedError): NextResponse {
  return NextResponse.json(
    {
      code: "plan_access_denied",
      message: error.message
    },
    { status: error.status }
  );
}

function backendErrorResponse(error: BackendApiError): NextResponse {
  return NextResponse.json(error.payload ?? { message: error.message }, { status: error.status });
}

async function resolveSession(
  accessToken: string,
  refreshToken: string | undefined,
  forwardedFor: string | undefined
): Promise<{ session: AuthSession; accessToken: string; refreshedTokens?: BackendRefreshResponse } | NextResponse> {
  try {
    const session = await meWithBackend(accessToken, forwardedFor);
    return { session, accessToken };
  } catch (error) {
    if (!(error instanceof BackendApiError) || error.status !== 401 || !refreshToken) {
      if (error instanceof BackendApiError && error.status !== 401) {
        return backendErrorResponse(error);
      }
      return unauthorizedResponse();
    }

    try {
      const refreshedTokens = await refreshWithBackend(refreshToken, forwardedFor);
      const session = await meWithBackend(refreshedTokens.access_token, forwardedFor);
      return {
        session,
        accessToken: refreshedTokens.access_token,
        refreshedTokens
      };
    } catch (refreshError) {
      if (refreshError instanceof BackendApiError && refreshError.status !== 401) {
        return backendErrorResponse(refreshError);
      }
      return unauthorizedResponse();
    }
  }
}

export async function runWithBackendSession<T>(
  request: NextRequest,
  task: (accessToken: string) => Promise<T>
): Promise<SessionSuccess<T> | NextResponse> {
  const accessToken = request.cookies.get(ACCESS_COOKIE_NAME)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;
  const forwardedFor = resolveForwardedFor(request);

  if (!accessToken) {
    return unauthorizedResponse();
  }

  const sessionResult = await resolveSession(accessToken, refreshToken, forwardedFor);
  if ("status" in sessionResult) {
    return sessionResult;
  }

  try {
    const data = await task(sessionResult.accessToken);
    return {
      data,
      refreshedTokens: sessionResult.refreshedTokens,
      workspaceId: sessionResult.session.workspaceId
    };
  } catch (error) {
    if (error instanceof BackendApiError) {
      return backendErrorResponse(error);
    }

    if (error instanceof WorkspaceScopeError) {
      return forbiddenWorkspaceResponse({
        expectedWorkspaceId: error.expectedWorkspaceId,
        actualWorkspaceId: error.actualWorkspaceId
      });
    }

    if (error instanceof RbacForbiddenError) {
      return forbiddenRoleResponse(error);
    }

    if (error instanceof PlanLimitExceededError) {
      return planLimitExceededResponse(error);
    }

    if (error instanceof PlanAccessDeniedError) {
      return planAccessDeniedResponse(error);
    }

    return NextResponse.json({ message: "Unexpected backend failure" }, { status: 500 });
  }
}

export async function runWithWorkspaceSession<T>(
  request: NextRequest,
  task: (context: WorkspaceContext) => Promise<T>
): Promise<SessionSuccess<T> | NextResponse> {
  const accessToken = request.cookies.get(ACCESS_COOKIE_NAME)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE_NAME)?.value;
  const cookieWorkspaceId = request.cookies.get(WORKSPACE_COOKIE_NAME)?.value;
  const forwardedFor = resolveForwardedFor(request);

  if (!accessToken) {
    return unauthorizedResponse();
  }

  const sessionResult = await resolveSession(accessToken, refreshToken, forwardedFor);
  if ("status" in sessionResult) {
    return sessionResult;
  }

  const sessionWorkspaceId = sessionResult.session.workspaceId;
  if (cookieWorkspaceId && cookieWorkspaceId !== sessionWorkspaceId) {
    return forbiddenWorkspaceResponse({
      expectedWorkspaceId: sessionWorkspaceId,
      actualWorkspaceId: cookieWorkspaceId
    });
  }

  try {
    const data = await task({
      accessToken: sessionResult.accessToken,
      workspaceId: sessionWorkspaceId,
      userId: sessionResult.session.user.id,
      role: sessionResult.session.role,
      session: sessionResult.session,
      forwardedFor
    });

    return {
      data,
      refreshedTokens: sessionResult.refreshedTokens,
      workspaceId: sessionWorkspaceId
    };
  } catch (error) {
    if (error instanceof BackendApiError) {
      return backendErrorResponse(error);
    }

    if (error instanceof WorkspaceScopeError) {
      return forbiddenWorkspaceResponse({
        expectedWorkspaceId: error.expectedWorkspaceId,
        actualWorkspaceId: error.actualWorkspaceId
      });
    }

    if (error instanceof RbacForbiddenError) {
      return forbiddenRoleResponse(error);
    }

    if (error instanceof PlanLimitExceededError) {
      return planLimitExceededResponse(error);
    }

    if (error instanceof PlanAccessDeniedError) {
      return planAccessDeniedResponse(error);
    }

    return NextResponse.json({ message: "Unexpected backend failure" }, { status: 500 });
  }
}

export function withSessionJson<T>(payload: SessionSuccess<T>): NextResponse {
  const response = NextResponse.json(payload.data);
  if (payload.refreshedTokens) {
    setSessionCookies(response, payload.refreshedTokens);
  }
  if (payload.workspaceId) {
    setActiveWorkspaceCookie(response, payload.workspaceId);
  }
  return response;
}
