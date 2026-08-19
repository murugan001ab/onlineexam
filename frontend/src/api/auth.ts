import { apiClient, tokenStorage } from "@/api/client";
import type {
  ChangePasswordRequest,
  LoginRequest,
  MeResponse,
  TokenResponse,
} from "@/types/auth";

export async function login(payload: LoginRequest): Promise<MeResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
  tokenStorage.setTokens(data.access_token, data.refresh_token);
  return fetchMe();
}

export async function fetchMe(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>("/auth/me");
  return data;
}

export async function changePassword(payload: ChangePasswordRequest): Promise<void> {
  await apiClient.post("/auth/change-password", payload);
}

export function logout() {
  tokenStorage.clear();
}

export async function redeemInvitation(token: string, new_password: string): Promise<MeResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/redeem-invitation", { token, new_password });
  tokenStorage.setTokens(data.access_token, data.refresh_token);
  return fetchMe();
}
