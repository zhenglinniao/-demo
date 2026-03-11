import { Bot, BotCreate, Conversation, Group, GroupBot, Message } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await res.text();
  let data: any;
  try {
    data = JSON.parse(text);
  } catch {
    data = { raw: text };
  }
  if (!res.ok) throw data;
  return data as T;
}

export async function login(username: string, password: string) {
  return request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function register(username: string, password: string) {
  return request<{ access_token: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function listConversations(token: string, tags?: string) {
  const query = tags ? `?tags=${encodeURIComponent(tags)}` : "";
  return request<Conversation[]>(`/conversations${query}`, {}, token);
}

export async function createConversation(token: string, title?: string, tags?: string[]) {
  return request<Conversation>(
    "/conversations",
    { method: "POST", body: JSON.stringify({ title: title || null, tags: tags || [] }) },
    token
  );
}

export async function updateConversation(
  token: string,
  id: number,
  payload: { title?: string | null; tags?: string[] }
) {
  return request<Conversation>(`/conversations/${id}`, { method: "PATCH", body: JSON.stringify(payload) }, token);
}

export async function deleteConversation(token: string, id: number) {
  return request<{ status: string }>(`/conversations/${id}`, { method: "DELETE" }, token);
}

export async function listMessages(token: string, id: number) {
  return request<Message[]>(`/conversations/${id}/messages`, {}, token);
}

export async function sendMessage(token: string, id: number, content: string) {
  return request<{ user_message: Message; ai_message: Message; ai_error: boolean; error_message?: string }>(
    `/conversations/${id}/messages`,
    { method: "POST", body: JSON.stringify({ content }) },
    token
  );
}

export async function listGroups(token: string) {
  return request<Group[]>("/groups", {}, token);
}

export async function createGroup(token: string, payload: { title: string; bots: BotCreate[] }) {
  return request<Group>("/groups", { method: "POST", body: JSON.stringify(payload) }, token);
}

export async function updateGroup(token: string, id: number, title: string) {
  return request<Group>(`/groups/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }, token);
}

export async function deleteGroup(token: string, id: number) {
  return request<{ status: string }>(`/groups/${id}`, { method: "DELETE" }, token);
}

export async function addGroupMember(token: string, groupId: number, username: string) {
  return request<{ status: string }>(
    `/groups/${groupId}/members`,
    { method: "POST", body: JSON.stringify({ username }) },
    token
  );
}

export async function listGroupMessages(token: string, groupId: number) {
  return request<Message[]>(`/groups/${groupId}/messages`, {}, token);
}

export async function sendGroupMessage(token: string, groupId: number, content: string) {
  return request<{ user_message: Message; bot_messages: Message[]; ai_error: boolean; error_message?: string }>(
    `/groups/${groupId}/messages`,
    { method: "POST", body: JSON.stringify({ content }) },
    token
  );
}

export async function listGroupBots(token: string, groupId: number) {
  return request<GroupBot[]>(`/groups/${groupId}/bots`, {}, token);
}

export async function listBots(token: string) {
  return request<Bot[]>("/bots", {}, token);
}
