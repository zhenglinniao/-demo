
"use client";

import { useEffect, useMemo, useState } from "react";
import {
  addGroupMember,
  createConversation,
  createGroup,
  deleteConversation,
  listBots,
  listConversations,
  listGroupBots,
  listGroupMessages,
  listGroups,
  listMessages,
  login,
  register,
  sendGroupMessage,
  sendMessage,
  updateConversation,
} from "@/lib/api";
import { Bot, Conversation, GroupBot, Message } from "@/lib/types";
import { Edit2, Plus, Trash2, Users } from "lucide-react";

const retry = async <T,>(fn: () => Promise<T>, times = 2): Promise<T> => {
  let lastErr: any;
  for (let i = 0; i <= times; i += 1) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr;
};

const labelForDate = (date: string) => {
  const d = new Date(date);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diff === 0) return "今天";
  if (diff === 1) return "昨天";
  return d.toLocaleDateString();
};

export default function Page() {
  const [token, setToken] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authForm, setAuthForm] = useState({ username: "", password: "" });
  const [authError, setAuthError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [groups, setGroups] = useState<{ id: number; title: string }[]>([]);
  const [bots, setBots] = useState<Bot[]>([]);
  const [groupBots, setGroupBots] = useState<GroupBot[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [activeGroupId, setActiveGroupId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [groupMessages, setGroupMessages] = useState<Message[]>([]);
  const [tagFilter, setTagFilter] = useState("");
  const [convTitle, setConvTitle] = useState("");
  const [convTags, setConvTags] = useState("");
  const [input, setInput] = useState("");
  const [groupInput, setGroupInput] = useState("");
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [groupTitle, setGroupTitle] = useState("");
  const [groupBotIds, setGroupBotIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (stored) setToken(stored);
  }, []);

  useEffect(() => {
    if (!token) return;
    listConversations(token, tagFilter || undefined)
      .then(setConversations)
      .catch(() => { });
    listGroups(token).then(setGroups).catch(() => { });
    listBots(token).then(setBots).catch(() => { });
  }, [token, tagFilter]);

  useEffect(() => {
    if (!token || !activeConversation) return;
    listMessages(token, activeConversation.id).then(setMessages).catch(() => { });
  }, [token, activeConversation]);

  useEffect(() => {
    if (!token || !activeGroupId) return;
    listGroupMessages(token, activeGroupId).then(setGroupMessages).catch(() => { });
    listGroupBots(token, activeGroupId).then(setGroupBots).catch(() => { });
  }, [token, activeGroupId]);

  const tagCloud = useMemo(() => {
    const map = new Map<string, number>();
    conversations.forEach((c) => c.tags.forEach((t) => map.set(t.name, (map.get(t.name) || 0) + 1)));
    return Array.from(map.entries()).map(([name, count]) => ({ name, count }));
  }, [conversations]);

  const groupedMessages = useMemo(() => groupByDate(messages), [messages]);
  const groupedGroupMessages = useMemo(() => groupByDate(groupMessages), [groupMessages]);
  const groupBotMap = useMemo(() => new Map(groupBots.map((b) => [b.bot_id, b])), [groupBots]);

  const handleAuth = async () => {
    setAuthError(null);
    try {
      const fn = authMode === "login" ? login : register;
      const data = await fn(authForm.username, authForm.password);
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
    } catch (err: any) {
      setAuthError("登录失败，请确认后端已启动并检查用户名/密码。");
    }
  };

  const handleCreateConversation = async () => {
    if (!token) return;
    const created = await createConversation(
      token,
      convTitle || undefined,
      convTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean)
    );
    setConversations((prev) => [created, ...prev]);
    setActiveConversation(created);
  };

  const handleUpdateConversation = async () => {
    if (!token || !activeConversation) return;
    const updated = await updateConversation(token, activeConversation.id, {
      title: convTitle || null,
      tags: convTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    });
    setConversations((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    setActiveConversation(updated);
  };

  const handleDeleteConversation = async (conv: Conversation) => {
    if (!token) return;
    await deleteConversation(token, conv.id);
    setConversations((prev) => prev.filter((c) => c.id !== conv.id));
    if (activeConversation?.id === conv.id) {
      setActiveConversation(null);
      setMessages([]);
    }
  };

  const handleSendMessage = async () => {
    if (!token || !activeConversation || !input.trim()) return;
    const optimistic: Message = {
      id: Date.now(),
      sender_type: "user",
      content: input,
      status: "ok",
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setInput("");
    setLoading(true);
    setErrorBanner(null);

    try {
      const data = await retry(() => sendMessage(token, activeConversation.id, optimistic.content), 2);
      setMessages((prev) => [...prev, data.ai_message]);
    } catch {
      setErrorBanner("AI 回复失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const handleSendGroupMessage = async () => {
    if (!token || !activeGroupId || !groupInput.trim()) return;
    const optimistic: Message = {
      id: Date.now(),
      sender_type: "user",
      content: groupInput,
      status: "ok",
      created_at: new Date().toISOString(),
    };
    setGroupMessages((prev) => [...prev, optimistic]);
    setGroupInput("");
    setLoading(true);
    setErrorBanner(null);

    try {
      const data = await retry(() => sendGroupMessage(token, activeGroupId, optimistic.content), 2);
      setGroupMessages((prev) => [...prev, ...data.bot_messages]);
    } catch {
      setErrorBanner("机器人回复失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroup = async () => {
    if (!token) return;
    const created = await createGroup(token, { title: groupTitle, bot_ids: groupBotIds });
    setGroups((prev) => [created, ...prev]);
    setGroupTitle("");
    setGroupBotIds([]);
    setGroupModalOpen(false);
  };

  const handleAddMember = async (username: string) => {
    if (!token || !activeGroupId || !username) return;
    await addGroupMember(token, activeGroupId, username);
  };

  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Minimal Chat</h1>
            <p className="text-sm text-muted">极简但完整的对话系统</p>
          </div>
          {token && (
            <button
              className="rounded-xl border border-border px-4 py-2 text-sm"
              onClick={() => {
                localStorage.removeItem("token");
                setToken("");
              }}
            >
              退出登录
            </button>
          )}
        </header>

        {!token ? (
          <section className="mt-8 max-w-md rounded-xl border border-border bg-white p-6">
            <div className="flex gap-2">
              <button
                className={`rounded-xl px-4 py-2 text-sm ${authMode === "login" ? "bg-bubbleUser text-white" : "border border-border"}`}
                onClick={() => setAuthMode("login")}
              >
                登录
              </button>
              <button
                className={`rounded-xl px-4 py-2 text-sm ${authMode === "register" ? "bg-bubbleUser text-white" : "border border-border"}`}
                onClick={() => setAuthMode("register")}
              >
                注册
              </button>
            </div>
            <div className="mt-4 space-y-3">
              <input
                className="w-full rounded-xl border border-border px-3 py-2"
                placeholder="用户名"
                value={authForm.username}
                onChange={(e) => setAuthForm((s) => ({ ...s, username: e.target.value }))}
              />
              <input
                type="password"
                className="w-full rounded-xl border border-border px-3 py-2"
                placeholder="密码"
                value={authForm.password}
                onChange={(e) => setAuthForm((s) => ({ ...s, password: e.target.value }))}
              />
              <button className="w-full rounded-xl bg-bubbleUser py-2 text-white" onClick={handleAuth}>
                {authMode === "login" ? "登录" : "注册"}
              </button>
            </div>
            <div className="mt-4 space-y-2">
              <button className="w-full rounded-xl border border-border py-2 text-sm">Google 登录（占位）</button>
              <button className="w-full rounded-xl border border-border py-2 text-sm">GitHub 登录（占位）</button>
            </div>
            {authError && <div className="mt-3 text-sm text-danger">{authError}</div>}
          </section>
        ) : (
          <section className="mt-8 grid grid-cols-[260px_1fr] gap-6">
            <aside className="rounded-xl border border-border bg-white p-4">
              <div className="space-y-2">
                <button className="flex w-full items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm" onClick={handleCreateConversation}>
                  <Plus size={14} /> 新建个人对话
                </button>
                <button className="flex w-full items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm" onClick={() => setGroupModalOpen(true)}>
                  <Users size={14} /> 新建群组对话
                </button>
              </div>

              <div className="mt-6">
                <div className="text-xs font-semibold text-muted">标签筛选</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {tagCloud.map((tag) => (
                    <button
                      key={tag.name}
                      className={`rounded-full border px-3 py-1 text-xs ${tagFilter === tag.name ? "border-bubbleUser text-bubbleUser" : "border-border"}`}
                      onClick={() => setTagFilter(tag.name)}
                    >
                      {tag.name} ({tag.count})
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-6">
                <div className="text-xs font-semibold text-muted">个人对话</div>
                <div className="mt-2 space-y-2">
                  {conversations.map((conv) => (
                    <div key={conv.id} className="rounded-xl border border-border p-2">
                      <div className="flex items-center justify-between">
                        <button
                          className="text-left text-sm"
                          onClick={() => {
                            setActiveConversation(conv);
                            setActiveGroupId(null);
                            setConvTitle(conv.title);
                            setConvTags(conv.tags.map((t) => t.name).join(","));
                          }}
                        >
                          {conv.title}
                        </button>
                        <div className="flex gap-2">
                          <button onClick={() => handleDeleteConversation(conv)}>
                            <Trash2 size={14} />
                          </button>
                          <button onClick={() => setActiveConversation(conv)}>
                            <Edit2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6">
                <div className="text-xs font-semibold text-muted">群组对话</div>
                <div className="mt-2 space-y-2">
                  {groups.map((group) => (
                    <button
                      key={group.id}
                      className="flex w-full items-center gap-2 rounded-xl border border-border px-3 py-2 text-left text-sm"
                      onClick={() => {
                        setActiveGroupId(group.id);
                        setActiveConversation(null);
                      }}
                    >
                      <Users size={14} /> {group.title}
                    </button>
                  ))}
                </div>
              </div>
            </aside>

            <main className="rounded-xl border border-border bg-white p-6">
              <div className="flex items-center justify-between">
                <div>
                  <input
                    className="text-xl font-semibold outline-none"
                    value={activeConversation?.title || "未选择对话"}
                    onChange={(e) => setConvTitle(e.target.value)}
                    onBlur={handleUpdateConversation}
                    disabled={!activeConversation}
                  />
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(activeConversation?.tags || []).map((t) => (
                      <span key={t.id} className="rounded-full border border-border px-3 py-1 text-xs">
                        {t.name}
                      </span>
                    ))}
                    {activeConversation && (
                      <button className="rounded-full border border-border px-3 py-1 text-xs" onClick={handleUpdateConversation}>
                        + 添加标签
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-6">
                {activeConversation &&
                  Object.entries(groupedMessages).map(([label, items]) => (
                    <div key={label} className="mb-6">
                      <div className="mb-3 text-xs text-muted">{label}</div>
                      <div className="space-y-3">
                        {items.map((m) => (
                          <div key={m.id} className={`flex ${m.sender_type === "user" ? "justify-end" : "justify-start"}`}>
                            <div
                              className={`chat-bubble ${m.sender_type === "user" ? "bg-bubbleUser text-white" : "bg-bubbleBot text-text"}`}
                            >
                              {m.content}
                            </div>
                          </div>
                        ))}
                        {loading && <div className="chat-bubble bg-bubbleBot text-text fade-pulse">生成中...</div>}
                      </div>
                    </div>
                  ))}

                {activeGroupId &&
                  Object.entries(groupedGroupMessages).map(([label, items]) => (
                    <div key={label} className="mb-6">
                      <div className="mb-3 text-xs text-muted">{label}</div>
                      <div className="space-y-3">
                        {items.map((m) => {
                          const bot = m.bot_id ? groupBotMap.get(m.bot_id) : null;
                          return (
                            <div key={m.id} className={`flex ${m.sender_type === "user" ? "justify-end" : "justify-start"}`}>
                              <div className="max-w-[70%]">
                                {bot && <div className="mb-1 text-xs text-muted">{bot.name} · {bot.persona}</div>}
                                <div
                                  className={`chat-bubble ${m.sender_type === "user" ? "bg-bubbleUser text-white" : "bg-bubbleBot text-text"}`}
                                >
                                  {m.content}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                        {loading && <div className="chat-bubble bg-bubbleBot text-text fade-pulse">生成中...</div>}
                      </div>
                    </div>
                  ))}
              </div>

              <div className="mt-6 rounded-xl border border-border p-3">
                <textarea
                  className="w-full rounded-xl border border-border px-3 py-2"
                  rows={3}
                  placeholder="输入消息"
                  value={activeGroupId ? groupInput : input}
                  onChange={(e) => (activeGroupId ? setGroupInput(e.target.value) : setInput(e.target.value))}
                />
                <div className="mt-2 flex items-center gap-2">
                  <button
                    className="rounded-xl bg-bubbleUser px-3 py-2 text-sm text-white"
                    onClick={activeGroupId ? handleSendGroupMessage : handleSendMessage}
                    disabled={!activeGroupId && !activeConversation}
                  >
                    发送
                  </button>
                  {errorBanner && (
                    <div className="text-sm text-danger">
                      {errorBanner}{" "}
                      <button className="underline" onClick={activeGroupId ? handleSendGroupMessage : handleSendMessage}>
                        🔄 点击重试
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </main>
          </section>
        )}
      </div>

      {groupModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white p-6">
            <div className="text-lg font-semibold">创建群组</div>
            <input
              className="mt-3 w-full rounded-xl border border-border px-3 py-2"
              placeholder="群组名称"
              value={groupTitle}
              onChange={(e) => setGroupTitle(e.target.value)}
            />
            <div className="mt-4">
              <div className="text-sm text-muted">选择机器人角色</div>
              <div className="mt-2 space-y-2">
                {bots
                  .filter((b) => ["CustomerBot", "TechBot", "HumorBot"].includes(b.name))
                  .map((bot) => (
                    <label key={bot.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={groupBotIds.includes(bot.id)}
                        onChange={(e) => {
                          setGroupBotIds((prev) =>
                            e.target.checked ? [...prev, bot.id] : prev.filter((id) => id !== bot.id)
                          );
                        }}
                      />
                      {bot.name}
                    </label>
                  ))}
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button className="rounded-xl border border-border px-3 py-2 text-sm" onClick={() => setGroupModalOpen(false)}>
                取消
              </button>
              <button className="rounded-xl bg-bubbleUser px-3 py-2 text-sm text-white" onClick={handleCreateGroup}>
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function groupByDate(items: Message[]) {
  const groups: Record<string, Message[]> = {};
  items.forEach((m) => {
    const label = labelForDate(m.created_at);
    if (!groups[label]) groups[label] = [];
    groups[label].push(m);
  });
  return groups;
}
