import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

const API_BASE = process.env.EXPO_PUBLIC_API_URL || "http://192.168.1.101:8001";

const MODES = [
  { id: "cloud", label: "Cloud", description: "Fast single-model answer." },
  { id: "council", label: "Council", description: "Autonomous roles, side-by-side answers." },
  { id: "debate", label: "Debate", description: "Roles, critique, revision, synthesis." },
];

const MODE_COLOR = {
  cloud: "#3b82f6",
  council: "#8b5cf6",
  debate: "#f59e0b",
};

function safeText(value) {
  if (!value) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function ProviderPill({ provider }) {
  const ready = provider.configured;
  return (
    <View style={[styles.providerPill, ready ? styles.providerReady : styles.providerMissing]}>
      <Text style={[styles.providerText, ready ? styles.providerReadyText : styles.providerMissingText]}>
        {provider.provider}
      </Text>
    </View>
  );
}

function RoleCard({ proposal }) {
  return (
    <View style={styles.roleCard}>
      <Text style={styles.roleProvider}>{proposal.provider}</Text>
      <Text style={styles.roleName}>{proposal.role}</Text>
      {!!proposal.reason && <Text style={styles.roleReason}>{proposal.reason}</Text>}
      {!proposal.autonomous && <Text style={styles.roleFallback}>Fallback role</Text>}
    </View>
  );
}

function ModelCard({ item }) {
  return (
    <View style={styles.modelCard}>
      <View style={styles.modelHeader}>
        <Text style={styles.modelProvider}>{item.provider}</Text>
        {!!item.role && <Text style={styles.modelRole}>{item.role}</Text>}
      </View>
      <Text style={styles.modelName}>{item.model}</Text>
      {item.error ? (
        <Text style={styles.modelError}>{safeText(item.error)}</Text>
      ) : (
        <Text style={styles.answerText}>{safeText(item.text || item.answer)}</Text>
      )}
    </View>
  );
}

function SectionToggle({ title, count, children }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={styles.section}>
      <Pressable style={styles.sectionButton} onPress={() => setOpen((value) => !value)}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Text style={styles.sectionMeta}>{count} {open ? "Hide" : "Show"}</Text>
      </Pressable>
      {open && <View style={styles.sectionBody}>{children}</View>}
    </View>
  );
}

function Results({ answer }) {
  if (!answer) return null;

  if (answer.mode === "cloud") {
    return (
      <View style={styles.resultBox}>
        <Text style={styles.resultTitle}>Answer</Text>
        <Text style={styles.answerText}>{safeText(answer.answer || answer.error)}</Text>
      </View>
    );
  }

  const roles = answer.role_proposals || [];
  const round1 = answer.round1 || answer.answer || [];
  const round2 = answer.round2 || [];
  const final = answer.final_answer || answer.final || "";

  return (
    <View style={styles.resultBox}>
      {roles.length > 0 && (
        <View style={styles.block}>
          <Text style={styles.resultTitle}>Autonomous Roles</Text>
          {roles.map((proposal) => (
            <RoleCard key={`${proposal.provider}-${proposal.role}`} proposal={proposal} />
          ))}
        </View>
      )}

      {!!final && (
        <View style={styles.block}>
          <View style={styles.finalHeader}>
            <Text style={styles.resultTitle}>Final Answer</Text>
            {!!answer.confidence && <Text style={styles.confidence}>{answer.confidence}</Text>}
          </View>
          {!!answer.confidence_reason && <Text style={styles.muted}>{answer.confidence_reason}</Text>}
          <Text style={styles.answerText}>{safeText(final)}</Text>
        </View>
      )}

      <SectionToggle title="Round 1" count={round1.length}>
        {round1.map((item) => (
          <ModelCard key={`${item.provider}-${item.model}-r1`} item={item} />
        ))}
      </SectionToggle>

      {round2.length > 0 && (
        <SectionToggle title="Round 2" count={round2.length}>
          {round2.map((item) => (
            <ModelCard key={`${item.provider}-${item.model}-r2`} item={item} />
          ))}
        </SectionToggle>
      )}
    </View>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("debate");
  const [providers, setProviders] = useState([]);
  const [answer, setAnswer] = useState(null);
  const [smart, setSmart] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  const activeMode = useMemo(() => MODES.find((item) => item.id === mode), [mode]);
  const activeColor = MODE_COLOR[mode] || MODE_COLOR.cloud;

  const requestJson = useCallback(async (path, payload) => {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Request failed");
    }
    return data;
  }, []);

  const refreshProviders = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/providers`);
      const data = await response.json();
      setProviders(data.providers || []);
    } catch {
      setProviders([]);
      setError(`Could not reach API at ${API_BASE}`);
    }
  }, []);

  useEffect(() => {
    refreshProviders();
  }, [refreshProviders]);

  async function analyzeSmart() {
    if (!prompt.trim()) {
      setError("Write a prompt first.");
      return;
    }
    setLoading(true);
    setError("");
    setAnswer(null);
    try {
      const data = await requestJson("/chat/smart/analyze", { prompt });
      setSmart(data);
      setMode(data.suggested_mode);
    } catch (err) {
      setError(err.message || "Smart analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function send(selectedMode = mode) {
    if (!prompt.trim()) {
      setError("Write a prompt first.");
      return;
    }

    const paths = {
      cloud: "/chat/cloud",
      council: "/chat/council",
      debate: "/chat/council/debate",
    };

    setLoading(true);
    setError("");
    setAnswer(null);
    setSmart(null);
    try {
      const data = await requestJson(paths[selectedMode], { prompt });
      setAnswer(data);
      setHistory((prev) => [{ prompt, mode: selectedMode, at: Date.now() }, ...prev].slice(0, 6));
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function shareAnswer() {
    const text = answer?.final_answer || answer?.answer || answer?.final;
    if (!text) {
      Alert.alert("Nothing to share yet");
      return;
    }
    await Share.share({ message: safeText(text) });
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={styles.safe} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>AI Council</Text>
              <Text style={styles.subtitle}>Autonomous multi-model reasoning.</Text>
            </View>
            <View style={styles.statusDot} />
          </View>

          <View style={styles.modeRow}>
            {MODES.map((item) => (
              <Pressable
                key={item.id}
                style={[styles.modeButton, mode === item.id && { borderColor: MODE_COLOR[item.id] }]}
                onPress={() => setMode(item.id)}
              >
                <Text style={[styles.modeText, mode === item.id && { color: MODE_COLOR[item.id] }]}>{item.label}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.modeDescription}>{activeMode?.description}</Text>

          <TextInput
            value={prompt}
            onChangeText={setPrompt}
            placeholder="Write your prompt here..."
            placeholderTextColor="#5a7499"
            multiline
            editable={!loading}
            style={[styles.input, { borderColor: prompt ? `${activeColor}88` : "#1a2d4a" }]}
          />

          <View style={styles.actionRow}>
            <Pressable
              style={[styles.primaryButton, { backgroundColor: activeColor }, loading && styles.disabled]}
              disabled={loading || !prompt.trim()}
              onPress={() => send()}
            >
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryText}>Send</Text>}
            </Pressable>
            <Pressable style={[styles.secondaryButton, loading && styles.disabled]} disabled={loading || !prompt.trim()} onPress={analyzeSmart}>
              <Text style={styles.secondaryText}>Smart</Text>
            </Pressable>
          </View>

          <View style={styles.providerRow}>
            {providers.map((provider) => (
              <ProviderPill key={`${provider.provider}-${provider.model}`} provider={provider} />
            ))}
          </View>

          {!!smart && (
            <View style={styles.smartBox}>
              <Text style={styles.resultTitle}>Smart Recommendation: {smart.suggested_mode}</Text>
              <Text style={styles.muted}>{smart.reason}</Text>
              <Pressable style={[styles.primaryButton, { backgroundColor: MODE_COLOR[smart.suggested_mode] || activeColor }]} onPress={() => send(smart.suggested_mode)}>
                <Text style={styles.primaryText}>Use {smart.suggested_mode}</Text>
              </Pressable>
            </View>
          )}

          {!!error && <Text style={styles.error}>{error}</Text>}

          {answer && (
            <>
              <Pressable style={styles.shareButton} onPress={shareAnswer}>
                <Text style={styles.secondaryText}>Share final answer</Text>
              </Pressable>
              <Results answer={answer} />
            </>
          )}

          {history.length > 0 && (
            <View style={styles.historyBox}>
              <Text style={styles.resultTitle}>Recent prompts</Text>
              {history.map((item) => (
                <Pressable
                  key={`${item.at}-${item.prompt}`}
                  style={styles.historyItem}
                  onPress={() => {
                    setPrompt(item.prompt);
                    setMode(item.mode);
                  }}
                >
                  <Text style={styles.historyMode}>{item.mode}</Text>
                  <Text style={styles.historyPrompt}>{item.prompt}</Text>
                </Pressable>
              ))}
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#070d1a",
  },
  page: {
    padding: 18,
    paddingBottom: 48,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 22,
  },
  title: {
    color: "#e2eaf7",
    fontSize: 31,
    fontWeight: "800",
  },
  subtitle: {
    color: "#5a7499",
    marginTop: 3,
    fontSize: 14,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#10b981",
    marginTop: 12,
  },
  modeRow: {
    flexDirection: "row",
    gap: 9,
    marginBottom: 10,
  },
  modeButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#1a2d4a",
    borderRadius: 10,
    paddingVertical: 11,
    backgroundColor: "#111e35",
    alignItems: "center",
  },
  modeText: {
    color: "#5a7499",
    fontWeight: "700",
  },
  modeDescription: {
    color: "#5a7499",
    fontSize: 13,
    marginBottom: 14,
  },
  input: {
    minHeight: 150,
    backgroundColor: "#111e35",
    borderWidth: 1,
    borderRadius: 14,
    color: "#e2eaf7",
    padding: 15,
    textAlignVertical: "top",
    fontSize: 15,
    lineHeight: 22,
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
    marginTop: 12,
    marginBottom: 12,
  },
  primaryButton: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryText: {
    color: "#fff",
    fontWeight: "800",
  },
  secondaryButton: {
    borderRadius: 14,
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "#1e3352",
    backgroundColor: "#111e35",
    justifyContent: "center",
  },
  secondaryText: {
    color: "#e2eaf7",
    fontWeight: "700",
  },
  disabled: {
    opacity: 0.5,
  },
  providerRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 14,
  },
  providerPill: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  providerReady: {
    backgroundColor: "#052e16",
    borderColor: "#166534",
  },
  providerMissing: {
    backgroundColor: "#2d0a0a",
    borderColor: "#7f1d1d",
  },
  providerText: {
    fontSize: 12,
    fontWeight: "800",
  },
  providerReadyText: {
    color: "#86efac",
  },
  providerMissingText: {
    color: "#fca5a5",
  },
  smartBox: {
    borderWidth: 1,
    borderColor: "#1a2d4a",
    backgroundColor: "#111e35",
    borderRadius: 14,
    padding: 16,
    gap: 12,
    marginBottom: 14,
  },
  error: {
    color: "#fca5a5",
    backgroundColor: "#2d0a0a",
    borderColor: "#7f1d1d",
    borderWidth: 1,
    padding: 12,
    borderRadius: 10,
    marginBottom: 14,
  },
  shareButton: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: "#1e3352",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    marginBottom: 10,
  },
  resultBox: {
    borderWidth: 1,
    borderColor: "#1a2d4a",
    borderRadius: 16,
    backgroundColor: "#0c1525",
    overflow: "hidden",
  },
  block: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#1a2d4a",
  },
  resultTitle: {
    color: "#e2eaf7",
    fontWeight: "800",
    fontSize: 15,
    marginBottom: 8,
  },
  muted: {
    color: "#5a7499",
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 10,
  },
  answerText: {
    color: "#dbe7f8",
    fontSize: 14,
    lineHeight: 21,
  },
  finalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 10,
  },
  confidence: {
    color: "#fb923c",
    fontWeight: "800",
    fontSize: 12,
  },
  roleCard: {
    backgroundColor: "#162038",
    borderColor: "#1e3352",
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginTop: 8,
  },
  roleProvider: {
    color: "#7db4ff",
    fontSize: 11,
    fontWeight: "900",
    textTransform: "uppercase",
  },
  roleName: {
    color: "#a78bfa",
    fontSize: 15,
    fontWeight: "800",
    marginTop: 3,
  },
  roleReason: {
    color: "#8aa6c9",
    fontSize: 12,
    marginTop: 5,
    lineHeight: 17,
  },
  roleFallback: {
    color: "#fbbf24",
    fontSize: 11,
    fontWeight: "800",
    marginTop: 6,
  },
  modelCard: {
    backgroundColor: "#0c1525",
    borderBottomWidth: 1,
    borderBottomColor: "#1a2d4a",
    padding: 14,
  },
  modelHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 10,
  },
  modelProvider: {
    color: "#e2eaf7",
    fontWeight: "800",
  },
  modelRole: {
    color: "#a78bfa",
    fontSize: 12,
    fontWeight: "800",
  },
  modelName: {
    color: "#5a7499",
    fontSize: 12,
    marginTop: 2,
    marginBottom: 9,
  },
  modelError: {
    color: "#fca5a5",
    lineHeight: 20,
  },
  section: {
    borderTopWidth: 1,
    borderTopColor: "#1a2d4a",
  },
  sectionButton: {
    padding: 15,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  sectionTitle: {
    color: "#e2eaf7",
    fontWeight: "800",
  },
  sectionMeta: {
    color: "#5a7499",
    fontSize: 13,
  },
  sectionBody: {
    borderTopWidth: 1,
    borderTopColor: "#1a2d4a",
  },
  historyBox: {
    marginTop: 22,
  },
  historyItem: {
    flexDirection: "row",
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#13223a",
    paddingVertical: 10,
  },
  historyMode: {
    color: "#3b82f6",
    fontSize: 11,
    fontWeight: "900",
    width: 56,
    textTransform: "uppercase",
  },
  historyPrompt: {
    color: "#8aa6c9",
    flex: 1,
  },
});
