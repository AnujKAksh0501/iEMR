import { useState, useRef, useEffect } from "react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Sparkles, Send, User } from "lucide-react";
import { toast } from "sonner";

const SUGGESTIONS = [
  "Summarize a SOAP note for a patient with type 2 diabetes.",
  "What are common drug interactions with warfarin?",
  "Give a differential diagnosis for acute chest pain.",
  "Draft discharge instructions after appendectomy.",
];

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setInput("");
    setLoading(true);
    try {
      const r = await api.post("/assistant/chat", { message: msg, session_id: sessionId });
      setSessionId(r.data.session_id);
      setMessages((m) => [...m, { role: "assistant", content: r.data.reply }]);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
    setLoading(false);
  };

  return (
    <div data-testid="page-assistant" className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col">
      <div className="mb-4">
        <h1 className="flex items-center gap-2 font-serif text-3xl">
          <Sparkles className="h-6 w-6 text-accent" /> MedAssist
        </h1>
        <p className="text-sm text-muted-foreground">AI clinical assistant — for clinician review, not a substitute for judgment.</p>
      </div>

      <Card className="card-shadow flex flex-1 flex-col overflow-hidden border-border/70">
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-accent/15 text-accent">
                <Sparkles className="h-7 w-7" />
              </div>
              <p className="mb-6 max-w-sm text-muted-foreground">Ask about clinical notes, medications, diagnoses or documentation.</p>
              <div className="grid w-full max-w-md gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} data-testid="suggestion-btn"
                    className="rounded-lg border border-border/70 bg-muted/40 px-4 py-2.5 text-left text-sm hover:bg-muted">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`} data-testid={`msg-${m.role}`}>
              {m.role === "assistant" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Sparkles className="h-4 w-4" />
                </div>
              )}
              <div className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"}`}>
                {m.content}
              </div>
              {m.role === "user" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent-foreground">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}
          {loading && <div className="text-sm text-muted-foreground">MedAssist is thinking…</div>}
          <div ref={endRef} />
        </div>

        <div className="border-t p-3">
          <div className="flex items-end gap-2">
            <Textarea
              data-testid="assistant-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Ask MedAssist…"
              rows={1}
              className="min-h-[44px] resize-none bg-background"
            />
            <Button onClick={() => send()} disabled={loading} data-testid="assistant-send-btn" className="h-11 rounded-full px-4">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
