export type Tag = { id: number; name: string };

export type Conversation = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  tags: Tag[];
};

export type Message = {
  id: number;
  sender_type: "user" | "assistant" | "bot";
  content: string;
  status: "ok" | "error";
  error_message?: string | null;
  created_at: string;
  bot_id?: number | null;
};

export type Group = { id: number; title: string; created_at: string };

export type Bot = { id: number; name: string; persona: string };

export type GroupBot = {
  bot_id: number;
  name: string;
  persona: string;
};

export type BotCreate = { name: string; persona: string };
