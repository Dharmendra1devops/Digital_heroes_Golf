export type Account = {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_subscriber: boolean;
  subscription_renews_at: string | null;
};

export type GolfScore = {
  id: string;
  score_date: string;
  score: number;
  created_at: string;
};

export type Charity = {
  id: string;
  slug: string;
  name: string;
  description: string;
  image_path: string;
  website: string;
  is_featured: boolean;
  upcoming_events: Array<{
    id: string;
    title: string;
    description: string;
    starts_at: string;
    ends_at: string | null;
    location: string;
    image_path: string;
  }>;
};

export type CharitySelection = {
  id: string;
  charity: Charity;
  contribution_bps: number;
  effective_from: string;
  effective_to: string | null;
};

export type SubscriptionPlan = {
  id: string;
  interval: "monthly" | "yearly";
  amount_minor: number;
  currency: string;
  checkout_available: boolean;
};

export type AdminSubscriptionPlan = Omit<SubscriptionPlan, "checkout_available"> & {
  stripe_price_id: string | null;
  is_active: boolean;
};

export type MemberSubscription = {
  id: string;
  plan: SubscriptionPlan;
  status: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
  ended_at: string | null;
};

export type DrawConfiguration = {
  id: string;
  version: number;
  mode: "random" | "algorithmic";
  candidate_min: number;
  candidate_max: number;
  number_count: number;
  prize_pool_contribution_bps: number | null;
  parameters: Record<string, unknown>;
  prize_tiers: Array<{ match_count: number; share_bps: number; rollover_unclaimed: boolean }>;
};

export type DrawRecord = {
  id: string;
  configuration: string;
  scheduled_at: string;
  eligibility_cutoff: string;
  status: "draft" | "simulated" | "published" | "cancelled";
  configuration_snapshot: Record<string, unknown>;
  published_at: string | null;
  winning_numbers: number[];
  prize_pools: Array<{
    match_count: number;
    share_bps: number;
    available_minor: number;
    rollover_in_minor: number;
    rollover_out_minor: number;
    currency: string;
  }>;
};

export type MemberDrawSummary = {
  draws_entered: number;
  upcoming_draws: Array<{
    id: string;
    scheduled_at: string;
    entered: boolean;
  }>;
  winnings_by_currency: Array<{ currency: string; amount_minor: number }>;
  payouts_by_status: Array<{
    status: "pending" | "paid" | "failed";
    currency: string;
    amount_minor: number;
    count: number;
  }>;
};

export type DonationConfig = {
  currency: string;
  minimum_minor: number;
  maximum_minor: number;
  checkout_available: boolean;
};

export type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  date_joined: string;
  is_admin: boolean;
  subscriptions: Array<{
    id: string;
    plan_interval: "monthly" | "yearly";
    status: string;
    current_period_start: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
  }>;
  scores: Array<{ id: string; score_date: string; score: number }>;
};

export type AdminOverview = {
  total_users: number;
  active_subscribers: number;
  prize_funding_by_currency: Array<{ currency: string; amount_minor: number }>;
  charity_contributions_by_currency: Array<{ currency: string; amount_minor: number }>;
  draws_by_status: Array<{ status: string; count: number }>;
  distributed_pools_by_currency: Array<{ currency: string; distributed_minor: number }>;
  top_charities: Array<{ id: string; name: string; donations__currency: string; donation_total_minor: number }>;
  total_winners: number;
};

export type DrawRun = {
  id: string;
  draw: string;
  run_number: number;
  run_type: "simulation" | "publish";
  algorithm_version: string;
  input_hash: string;
  result_snapshot: {
    winning_numbers: number[];
    eligible_entry_count: number;
    matches: Array<{ entry_id: string; match_count: number }>;
    currency?: string;
    total_pool_minor?: number;
    winner_count?: number;
    prize_pools?: DrawRecord["prize_pools"];
  };
  audit_metadata: Record<string, unknown>;
  is_published: boolean;
  created_at: string;
};

export type MemberWinner = {
  id: string;
  draw_id: string;
  match_count: number;
  prize_amount_minor: number;
  currency: string;
  verification_status: "pending" | "approved" | "rejected";
  reviewed_at: string | null;
  review_reason: string;
  proofs: Array<{
    id: string;
    bucket: string;
    object_path: string;
    review_status: "pending" | "approved" | "rejected";
    submitted_at: string;
    review_reason: string;
  }>;
  payouts: Array<{
    id: string;
    amount_minor: number;
    currency: string;
    status: "pending" | "paid" | "failed";
    paid_at: string | null;
  }>;
};

export type AdminPayout = {
  id: string;
  winner: string;
  attempt_number: number;
  amount_minor: number;
  currency: string;
  status: "pending" | "paid" | "failed";
  provider_payout_id: string | null;
  paid_at: string | null;
  failure_reason: string;
  created_at: string;
};

export type AdminCharity = Charity & {
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
};

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function readCookie(name: string) {
  const entry = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));
  return entry ? decodeURIComponent(entry.slice(name.length + 1)) : null;
}

async function getCsrfToken() {
  let token = readCookie("csrftoken");
  if (!token) {
    const response = await fetch("/api/auth/csrf/", { credentials: "same-origin" });
    if (!response.ok) throw new ApiError("Unable to start a secure session.", response.status);
    token = readCookie("csrftoken");
  }
  if (!token) throw new ApiError("Security token is missing. Refresh and try again.", 0);
  return token;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const multipart = typeof FormData !== "undefined" && init.body instanceof FormData;
    if (!multipart) headers.set("Content-Type", "application/json");
    headers.set("X-CSRFToken", await getCsrfToken());
  }

  const response = await fetch(path, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
  });
  if (response.status === 204) return undefined as T;

  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  if (!response.ok) {
    const detail = payload.detail;
    const fieldError = Object.values(payload).find((value) => Array.isArray(value));
    const message =
      (typeof detail === "string" && detail) ||
      (Array.isArray(fieldError) && typeof fieldError[0] === "string" && fieldError[0]) ||
      "Something went wrong. Please try again.";
    throw new ApiError(message, response.status, typeof payload.code === "string" ? payload.code : undefined);
  }
  return payload as T;
}

export function getCurrentAccount() {
  return request<{ user: Account }>("/api/auth/me/");
}

export function updateMyProfile(input: { display_name: string }) {
  return request<{ user: Account }>("/api/auth/me/", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function changeMyPassword(input: { current_password: string; new_password: string }) {
  return request<{ detail: string }>("/api/auth/me/password/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getAdminUsers(query = "", page = 1) {
  const params = new URLSearchParams({ page: String(page) });
  if (query.trim()) params.set("q", query.trim());
  return request<{ count: number; next: string | null; results: AdminUser[] }>(
    `/api/auth/admin/users/?${params.toString()}`,
  );
}

export function updateAdminUser(id: string, input: Partial<Pick<AdminUser, "email" | "display_name" | "is_active">>) {
  return request<AdminUser>(`/api/auth/admin/users/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function updateAdminUserScore(userId: string, scoreId: string, input: { score?: number; score_date?: string }) {
  return request<AdminUser["scores"][number]>(`/api/auth/admin/users/${userId}/scores/${scoreId}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteAdminUserScore(userId: string, scoreId: string) {
  return request<void>(`/api/auth/admin/users/${userId}/scores/${scoreId}/`, { method: "DELETE" });
}

export function updateAdminSubscription(subscriptionId: string, action: "cancel" | "resume") {
  return request<{ subscription: AdminUser["subscriptions"][number] }>(
    `/api/subscriptions/admin/subscriptions/${subscriptionId}/action/`,
    {
      method: "POST",
      body: JSON.stringify({ action }),
    },
  );
}

export function getAdminOverview() {
  return request<AdminOverview>("/api/auth/admin/overview/");
}

export function registerAccount(input: {
  email: string;
  display_name: string;
  password: string;
  charity_id?: string;
  contribution_bps?: number;
}) {
  return request<{ user: Account }>("/api/auth/register/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function logIn(input: { email: string; password: string }) {
  return request<{ user: Account }>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function logOut() {
  return request<void>("/api/auth/logout/", { method: "POST" });
}

export function getScores() {
  return request<GolfScore[]>("/api/scores/");
}

export function createScore(input: { score_date: string; score: number }) {
  return request<GolfScore>("/api/scores/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateScore(id: string, input: { score: number }) {
  return request<GolfScore>(`/api/scores/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function removeScore(id: string) {
  return request<void>(`/api/scores/${id}/`, { method: "DELETE" });
}

export function getCharities(query = "") {
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  const suffix = params.size ? `?${params.toString()}` : "";
  return request<Charity[]>(`/api/charities/${suffix}`);
}

export function getCharity(slug: string) {
  return request<Charity>(`/api/charities/${encodeURIComponent(slug)}/`);
}

export function getCharitySelection() {
  return request<{ selection: CharitySelection | null }>("/api/charities/selection/");
}

export function saveCharitySelection(input: { charity_id: string; contribution_bps: number }) {
  return request<{ selection: CharitySelection }>("/api/charities/selection/", {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function getAdminCharities() {
  return request<AdminCharity[]>("/api/charities/admin/");
}

export function createAdminCharity(input: {
  slug: string;
  name: string;
  description: string;
  image_path: string;
  website: string;
  is_featured: boolean;
  is_active: boolean;
}) {
  return request<AdminCharity>("/api/charities/admin/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateAdminCharity(id: string, input: Partial<AdminCharity>) {
  return request<AdminCharity>(`/api/charities/admin/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteAdminCharity(id: string) {
  return request<void>(`/api/charities/admin/${id}/`, { method: "DELETE" });
}

export function getSubscriptionPlans() {
  return request<SubscriptionPlan[]>("/api/subscriptions/plans/");
}

export function getMySubscription() {
  return request<{ subscription: MemberSubscription | null }>("/api/subscriptions/me/");
}

export function cancelMySubscription() {
  return request<{ subscription: MemberSubscription }>("/api/subscriptions/me/cancel/", { method: "POST" });
}

export function resumeMySubscription() {
  return request<{ subscription: MemberSubscription }>("/api/subscriptions/me/resume/", { method: "POST" });
}

export function changeMySubscriptionPlan(planId: string) {
  return request<{ subscription: MemberSubscription }>("/api/subscriptions/me/change-plan/", {
    method: "POST",
    body: JSON.stringify({ plan_id: planId }),
  });
}

export function createCheckoutSession(interval: SubscriptionPlan["interval"]) {
  return request<{ checkout_url: string }>("/api/subscriptions/checkout/", {
    method: "POST",
    body: JSON.stringify({ interval }),
  });
}

export function getAdminSubscriptionPlans() {
  return request<AdminSubscriptionPlan[]>("/api/subscriptions/admin/plans/");
}

export function createAdminSubscriptionPlan(input: {
  interval: SubscriptionPlan["interval"];
  amount_minor: number;
  currency: string;
  stripe_price_id: string;
  is_active: boolean;
}) {
  return request<AdminSubscriptionPlan>("/api/subscriptions/admin/plans/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateAdminSubscriptionPlan(id: string, input: Partial<AdminSubscriptionPlan>) {
  return request<AdminSubscriptionPlan>(`/api/subscriptions/admin/plans/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function getPublicDraws() {
  return request<DrawRecord[]>("/api/draws/");
}

export function getMyDrawSummary() {
  return request<MemberDrawSummary>("/api/draws/me/summary/");
}

export function getDonationConfig() {
  return request<DonationConfig>("/api/payments/donations/config/");
}

export function createDonationCheckout(input: { charity_id: string; amount_minor: number }) {
  return request<{ checkout_url: string }>("/api/payments/donations/checkout/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getAdminDrawConfigurations() {
  return request<DrawConfiguration[]>("/api/draws/admin/configurations/");
}

export function createAdminDrawConfiguration(input: {
  version: number;
  mode: DrawConfiguration["mode"];
  candidate_min: number;
  candidate_max: number;
  number_count: number;
  prize_pool_contribution_bps: number;
  parameters: Record<string, unknown>;
}) {
  return request<DrawConfiguration>("/api/draws/admin/configurations/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getAdminDraws() {
  return request<DrawRecord[]>("/api/draws/admin/");
}

export function createAdminDraw(input: {
  configuration: string;
  scheduled_at: string;
  eligibility_cutoff: string;
}) {
  return request<DrawRecord>("/api/draws/admin/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function simulateAdminDraw(id: string) {
  return request<{ run: DrawRun }>(`/api/draws/admin/${id}/simulate/`, { method: "POST" });
}

export function publishAdminDraw(id: string) {
  return request<{ run: DrawRun }>(`/api/draws/admin/${id}/publish/`, { method: "POST" });
}

export function getMyWinners() {
  return request<MemberWinner[]>("/api/winners/me/");
}

export function uploadWinnerProof(winnerId: string, file: File) {
  const body = new FormData();
  body.append("proof", file);
  return request<MemberWinner["proofs"][number]>(`/api/winners/${winnerId}/proofs/`, {
    method: "POST",
    body,
  });
}

export function getAdminWinners(statusFilter?: string) {
  const suffix = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
  return request<MemberWinner[]>(`/api/winners/admin/${suffix}`);
}

export function getAdminProofUrl(proofId: string) {
  return request<{ signed_url: string; expires_in: number }>(`/api/winners/admin/proofs/${proofId}/signed-url/`);
}

export function reviewWinnerProof(proofId: string, review_status: "approved" | "rejected", review_reason: string) {
  return request<MemberWinner["proofs"][number]>(`/api/winners/admin/proofs/${proofId}/review/`, {
    method: "PATCH",
    body: JSON.stringify({ review_status, review_reason }),
  });
}

export function getAdminPayouts() {
  return request<AdminPayout[]>("/api/winners/admin/payouts/");
}

export function updateAdminPayout(
  payoutId: string,
  input: { status: "paid" | "failed"; provider_payout_id?: string; failure_reason?: string },
) {
  return request<AdminPayout>(`/api/winners/admin/payouts/${payoutId}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
