import { useState, useEffect, useRef, type FormEvent } from "react";
import {
  Routes,
  Route,
  Link,
  NavLink,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  Waves,
  ArrowUpRight,
  ArrowRight,
  MapPin,
  Mic,
  Upload,
  Check,
  ShieldCheck,
  LayoutDashboard,
  ChartNoAxesCombined,
  Send,
  Settings,
  LogOut,
  Search,
  X,
  RefreshCw,
  Download,
  Users,
  MessageSquare,
  Clock,
  Volume2,
  AlertTriangle,
  Languages,
  Navigation,
  StopCircle,
  Copy,
} from "lucide-react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api, base, type Incident } from "./api";
const date = (d: string) =>
  new Date(d).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
const nice = (s: string) => s?.replaceAll("_", " ") || "Unknown";
// crypto.randomUUID is only available in secure contexts (HTTPS or localhost).
const newKey = () =>
  globalThis.crypto?.randomUUID?.() ??
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
const LANGUAGE_KEY = "awaazsetu_language";
const MAX_RECORDING_SECONDS = 120;
function storedLanguage(): "en" | "hi" | "mr" {
  try {
    const value = localStorage.getItem(LANGUAGE_KEY);
    if (value === "en" || value === "hi" || value === "mr") return value;
  } catch {}
  return "mr";
}
const translations = {
  en: {
    title: "A voice that reaches. A community that responds.",
    intro:
      "Share what is happening around you. Your report helps coordinators understand local flood conditions.",
    report: "Report an incident",
    text: "Describe the situation",
    placeholder:
      "What happened? How many people need help? Mention a nearby landmark and the water level.",
    voice: "Prefer to speak?",
    record: "Record a voice message",
    upload: "Upload audio",
    location: "Your location",
    gps: "Use my current location",
    contact: "Phone number (optional; SMS replies not enabled)",
    consent:
      "I agree to share this report with coordinators for this drill. If AI is enabled, report text or audio may be sent to the configured AI provider.",
    submit: "Send report",
    language: "Report language",
    ticket: "Your voice has been received",
    tracking: "Track your report",
    preview: "Transcribe and review",
    reviewed: "I reviewed this transcript and corrected any errors.",
    previewHint:
      "Review the transcription before sending. You can edit every word.",
    transcribing: "Transcribing…",
    stop: "Stop recording",
    findingLocation: "Finding location…",
    gpsDenied:
      "Location permission was denied. Mention a nearby landmark in your report instead.",
    gpsFailed:
      "Could not find your location. Mention a nearby landmark in your report instead.",
    clearLocation: "Remove location",
    copyLink: "Copy tracking link",
    copied: "Link copied",
    another: "Submit another report",
    sending: "Sending…",

    privacy:
      "Your report is shared with the private coordination team. Your contact details are not displayed publicly.",
  },
  hi: {
    title: "आपकी आवाज़ पहुँचे। समुदाय साथ आए।",
    intro:
      "अपने आसपास की स्थिति बताएं। आपकी रिपोर्ट बाढ़ की स्थानीय स्थिति समझने में मदद करती है।",
    report: "घटना की रिपोर्ट करें",
    text: "स्थिति बताएं",
    placeholder:
      "क्या हुआ? कितने लोगों को मदद चाहिए? पास का स्थान और पानी का स्तर बताएं।",
    voice: "बोलकर बताना चाहते हैं?",
    record: "आवाज़ रिकॉर्ड करें",
    upload: "ऑडियो अपलोड करें",
    location: "आपका स्थान",
    gps: "मेरा वर्तमान स्थान जोड़ें",
    contact: "फ़ोन नंबर (वैकल्पिक; SMS उत्तर अभी बंद हैं)",
    consent:
      "मैं इस अभ्यास के लिए रिपोर्ट समन्वयकों के साथ साझा करने की सहमति देता/देती हूं। AI सक्षम होने पर रिपोर्ट का पाठ या ऑडियो चुने गए AI प्रदाता को भेजा जा सकता है।",
    submit: "रिपोर्ट भेजें",
    language: "रिपोर्ट की भाषा",
    ticket: "आपकी आवाज़ मिल गई है",
    tracking: "अपनी रिपोर्ट देखें",
    preview: "लिप्यंतरण करें और जाँचें",
    reviewed: "मैंने इस पाठ की जाँच की और गलतियाँ सुधारी हैं।",
    previewHint: "भेजने से पहले पाठ जाँचें। आप हर शब्द बदल सकते हैं।",
    transcribing: "लिप्यंतरण जारी है…",
    stop: "रिकॉर्डिंग रोकें",
    findingLocation: "स्थान खोजा जा रहा है…",
    gpsDenied:
      "स्थान की अनुमति नहीं मिली। कृपया रिपोर्ट में पास का स्थान लिखें।",
    gpsFailed: "आपका स्थान नहीं मिला। कृपया रिपोर्ट में पास का स्थान लिखें।",
    clearLocation: "स्थान हटाएं",
    copyLink: "ट्रैकिंग लिंक कॉपी करें",
    copied: "लिंक कॉपी हो गया",
    another: "एक और रिपोर्ट भेजें",
    sending: "भेजा जा रहा है…",

    privacy:
      "आपकी रिपोर्ट केवल निजी समन्वय टीम से साझा की जाती है। संपर्क विवरण सार्वजनिक नहीं हैं।",
  },
  mr: {
    title: "आवाज पोहोचेल. समुदाय प्रतिसाद देईल.",
    intro:
      "तुमच्या आसपासची परिस्थिती सांगा. तुमचा अहवाल स्थानिक पुराची स्थिती समजण्यास मदत करतो.",
    report: "घटनेची माहिती द्या",
    text: "परिस्थिती सांगा",
    placeholder:
      "काय घडले? किती लोकांना मदत हवी? जवळची खूण आणि पाण्याची पातळी सांगा.",
    voice: "बोलून सांगायचे आहे?",
    record: "आवाज रेकॉर्ड करा",
    upload: "ऑडिओ अपलोड करा",
    location: "तुमचे ठिकाण",
    gps: "माझे सध्याचे ठिकाण जोडा",
    contact: "फोन नंबर (ऐच्छिक; SMS उत्तर अद्याप बंद आहेत)",
    consent:
      "या सरावासाठी माझा अहवाल समन्वयकांशी शेअर करण्यास मी सहमत आहे. AI सुरू असल्यास अहवालाचा मजकूर किंवा ऑडिओ निवडलेल्या AI सेवेकडे पाठवला जाऊ शकतो.",
    submit: "अहवाल पाठवा",
    language: "अहवालाची भाषा",
    ticket: "तुमची माहिती मिळाली आहे",
    tracking: "तुमचा अहवाल पाहा",
    preview: "आवाजाचा मजकूर करा आणि तपासा",
    reviewed: "मी हा मजकूर तपासला आणि चुका दुरुस्त केल्या आहेत.",
    previewHint: "पाठवण्यापूर्वी मजकूर तपासा. प्रत्येक शब्द बदलता येतो.",
    transcribing: "मजकूर तयार होत आहे…",
    stop: "रेकॉर्डिंग थांबवा",
    findingLocation: "ठिकाण शोधत आहे…",
    gpsDenied: "ठिकाणाची परवानगी मिळाली नाही. अहवालात जवळची खूण लिहा.",
    gpsFailed: "तुमचे ठिकाण सापडले नाही. अहवालात जवळची खूण लिहा.",
    clearLocation: "ठिकाण काढा",
    copyLink: "ट्रॅकिंग लिंक कॉपी करा",
    copied: "लिंक कॉपी झाली",
    another: "आणखी एक अहवाल पाठवा",
    sending: "पाठवत आहे…",

    privacy:
      "तुमचा अहवाल फक्त खाजगी समन्वय टीमसोबत शेअर केला जातो. संपर्क माहिती सार्वजनिक दिसत नाही.",
  },
};
function Brand() {
  return (
    <Link to="/" className="brand">
      <span className="brand-icon">
        <Waves size={24} />
      </span>
      <span>
        AwaazSetu<small>EVERY VOICE MATTERS</small>
      </span>
    </Link>
  );
}
function ErrorBox({ text }: { text: string }) {
  return text ? (
    <div role="alert" className="error">
      <AlertTriangle size={18} />
      {text}
    </div>
  ) : null;
}
function Drill() {
  const [demo, setDemo] = useState<boolean | null>(null);
  useEffect(() => {
    api("/health")
      .then((d) => setDemo(d.demo))
      .catch(() => setDemo(null));
  }, []);
  return (
    <div className="drill">
      <ShieldCheck size={14} />
      {demo === true ? "COMMUNITY DRILL · " : ""}Coordination prototype · Not an
      emergency response service. For urgent help, contact local emergency
      services.
    </div>
  );
}
function PublicHeader() {
  return (
    <>
      <Drill />
      <header className="public-header">
        <Brand />
        <Link to="/console" className="subtle-link">
          Coordinator console <ArrowUpRight size={16} />
        </Link>
      </header>
    </>
  );
}
function Resident() {
  const [language, setLanguage] =
    useState<keyof typeof translations>(storedLanguage);
  const t = translations[language];
  const [text, setText] = useState(""),
    [contact, setContact] = useState(""),
    [consent, setConsent] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState<any>(null),
    [coords, setCoords] = useState<{
      latitude: number;
      longitude: number;
    } | null>(null),
    [gpsBusy, setGpsBusy] = useState(false),
    [audio, setAudio] = useState<Blob | null>(null),
    [recording, setRecording] = useState(false),
    [transcribing, setTranscribing] = useState(false),
    [hasTranscript, setHasTranscript] = useState(false),
    [reviewed, setReviewed] = useState(false),
    [audioUrl, setAudioUrl] = useState(""),
    [seconds, setSeconds] = useState(0),
    [copied, setCopied] = useState(false);
  const audioVersion = useRef(0);
  // One key per draft, so retrying after a lost response cannot create a duplicate report.
  const draftKey = useRef(newKey());
  useEffect(() => {
    try {
      localStorage.setItem(LANGUAGE_KEY, language);
    } catch {}
  }, [language]);
  useEffect(() => {
    if (!recording) return;
    setSeconds(0);
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [recording]);
  useEffect(() => {
    if (recording && seconds >= MAX_RECORDING_SECONDS) recorder.current?.stop();
  }, [recording, seconds]);
  const recorder = useRef<MediaRecorder | null>(null),
    chunks = useRef<Blob[]>([]);
  useEffect(
    () => () => {
      recorder.current?.stream.getTracks().forEach((t) => t.stop());
    },
    [],
  );
  useEffect(() => {
    if (!audio) {
      setAudioUrl("");
      return;
    }
    const url = URL.createObjectURL(audio);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audio]);
  function changeAudio(value: Blob | null) {
    audioVersion.current += 1;
    setAudio(value);
    setHasTranscript(false);
    setReviewed(false);
    setText("");
    setError("");
  }
  async function transcribe() {
    if (!audio || !consent) return;
    const version = audioVersion.current;
    setTranscribing(true);
    setError("");
    setHasTranscript(false);
    setReviewed(false);
    try {
      const f = new FormData();
      f.append(
        "audio",
        audio,
        audio instanceof File
          ? audio.name
          : "voice." + (audio.type.includes("mp4") ? "m4a" : "webm"),
      );
      f.append("language", language);
      f.append("consent", "true");
      const r = await api("/transcriptions", { method: "POST", body: f });
      if (version === audioVersion.current) {
        setText(r.text);
        setHasTranscript(true);
      }
    } catch (e) {
      if (version === audioVersion.current) setError((e as Error).message);
    } finally {
      setTranscribing(false);
    }
  }
  async function record() {
    changeAudio(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
        throw new Error(
          "Voice recording is unavailable in this browser. Please upload an audio file.",
        );
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream);
      recorder.current = r;
      chunks.current = [];
      r.ondataavailable = (e) => chunks.current.push(e.data);
      r.onstop = () => {
        changeAudio(new Blob(chunks.current, { type: r.mimeType }));
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
      };
      r.start();
      setRecording(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function gps() {
    setGpsBusy(true);
    setError("");
    navigator.geolocation
      ? navigator.geolocation.getCurrentPosition(
          (p) => {
            setCoords({
              latitude: p.coords.latitude,
              longitude: p.coords.longitude,
            });
            setGpsBusy(false);
          },
          (e) => {
            setError(
              e.code === e.PERMISSION_DENIED ? t.gpsDenied : t.gpsFailed,
            );
            setGpsBusy(false);
          },
          { timeout: 15000, enableHighAccuracy: true },
        )
      : (setError(t.gpsFailed), setGpsBusy(false));
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (text.length > 4000)
        throw new Error("Please shorten the report to 4000 characters.");
      if (audio && (!hasTranscript || !reviewed))
        throw new Error(t.previewHint);
      const r = await api("/reports", {
        method: "POST",
        body: JSON.stringify({
          text,
          language,
          channel: audio ? "voice" : "web",
          contact: contact || undefined,
          consent,
          ...coords,
          idempotency_key: draftKey.current,
        }),
      });
      setResult(r);
    } catch (e) {
      // A rejected request saved nothing, so the next attempt gets a fresh key.
      // Network failures keep the key: the report may have been stored already.
      if (!(e instanceof TypeError)) draftKey.current = newKey();
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function startOver() {
    draftKey.current = newKey();
    setResult(null);
    setText("");
    changeAudio(null);
    setConsent(false);
    setCoords(null);
    setCopied(false);
    window.scrollTo({ top: 0 });
  }
  async function copyLink() {
    const url = `${window.location.origin}/track/${result.ticket_id}?token=${encodeURIComponent(result.tracking_token)}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      window.prompt(t.copyLink, url);
    }
  }
  return (
    <>
      <PublicHeader />
      <main className="resident">
        <section className="resident-story">
          <span className="eyebrow">PUNE · COMMUNITY FLOOD COORDINATION</span>
          <h1>{t.title}</h1>
          <p className="lead">{t.intro}</p>
          <div className="river-art" aria-hidden="true">
            <div className="sun" />
            <div className="building b1" />
            <div className="building b2" />
            <div className="building b3" />
            <div className="river r1" />
            <div className="river r2" />
            <div className="river r3" />
            <span className="art-label">
              <Waves size={18} /> Stronger, together.
            </span>
          </div>
          <div className="story-points">
            <span>
              <Languages /> Marathi · Hindi · English
            </span>
            <span>
              <ShieldCheck /> Private coordination
            </span>
            <span>
              <Volume2 /> Text and voice reports
            </span>
          </div>
          <p className="privacy">{t.privacy}</p>
        </section>
        <section className="report-card" lang={language}>
          {result ? (
            <div className="confirmation">
              <div className="success-icon">
                <Check size={36} />
              </div>
              <span className="eyebrow">REPORT RECEIVED</span>
              <h2>{t.ticket}</h2>
              <p>
                {result.duplicate
                  ? "This report had already reached us before the connection dropped. Use the tracking link from your first submission, if you saved it."
                  : result.acknowledgement}
              </p>
              <div className="ticket-box">
                <small>TICKET ID</small>
                <strong>{result.ticket_id}</strong>
              </div>
              {result.tracking_token && (
                <>
                  <Link
                    className="button primary"
                    to={`/track/${result.ticket_id}?token=${encodeURIComponent(result.tracking_token)}`}
                  >
                    {t.tracking}
                    <ArrowRight size={18} />
                  </Link>
                  <button className="button secondary" onClick={copyLink}>
                    {copied ? <Check size={17} /> : <Copy size={17} />}
                    {copied ? t.copied : t.copyLink}
                  </button>
                  <p className="muted">
                    Save this private tracking link to see updates. Receiving a
                    ticket does not guarantee a response.
                  </p>
                </>
              )}
              <button className="button ghost" onClick={startOver}>
                {t.another}
              </button>
            </div>
          ) : (
            <form onSubmit={submit}>
              <div className="form-heading">
                <span className="eyebrow">YOUR COMMUNITY. YOUR VOICE.</span>
                <h2>{t.report}</h2>
              </div>
              <label>
                {t.language}
                <select
                  value={language}
                  onChange={(e) => {
                    setLanguage(e.target.value as keyof typeof translations);
                    if (audio) {
                      audioVersion.current += 1;
                      setHasTranscript(false);
                      setReviewed(false);
                      setText("");
                    }
                  }}
                >
                  <option value="mr">मराठी · Marathi</option>
                  <option value="hi">हिन्दी · Hindi</option>
                  <option value="en">English</option>
                </select>
              </label>
              <label>
                {t.text}
                <textarea
                  value={text}
                  onChange={(e) => {
                    setText(e.target.value);
                    if (audio) setReviewed(false);
                  }}
                  placeholder={t.placeholder}
                  rows={5}
                  required
                  disabled={!!audio && !hasTranscript}
                  minLength={3}
                  maxLength={4000}
                />
              </label>
              {text.length > 3600 && (
                <small className="char-count" aria-live="polite">
                  {text.length} / 4000
                </small>
              )}
              <div className="voice-box">
                <span>{t.voice}</span>
                <div className="button-row">
                  <button
                    type="button"
                    className={`button ${recording ? "danger" : "secondary"}`}
                    onClick={() =>
                      recording ? recorder.current?.stop() : record()
                    }
                  >
                    {recording ? <StopCircle size={17} /> : <Mic size={17} />}{" "}
                    {recording
                      ? `${t.stop} · ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} / 2:00`
                      : t.record}
                  </button>
                  <label className="button ghost upload">
                    <Upload size={17} />
                    {t.upload}
                    <input
                      type="file"
                      accept="audio/*"
                      onChange={(e) => changeAudio(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
                {audio && (
                  <div className="audio-choice">
                    <Check size={15} /> Audio ready ·{" "}
                    {(audio.size / 1024).toFixed(0)} KB{" "}
                    <button
                      type="button"
                      onClick={() => changeAudio(null)}
                      aria-label="Remove audio"
                    >
                      <X size={15} />
                    </button>
                  </div>
                )}
                {audio && (
                  <>
                    <audio controls src={audioUrl} className="audio-preview" />
                    <button
                      type="button"
                      className="button secondary"
                      disabled={
                        !consent || transcribing || recording || hasTranscript
                      }
                      onClick={transcribe}
                    >
                      {transcribing ? t.transcribing : t.preview}
                    </button>
                    <small>{t.previewHint}</small>
                    {hasTranscript && (
                      <label className="checkbox transcript-review">
                        <input
                          type="checkbox"
                          checked={reviewed}
                          onChange={(e) => setReviewed(e.target.checked)}
                        />
                        <span>{t.reviewed}</span>
                      </label>
                    )}
                  </>
                )}
                <small>
                  Voice submission requires a configured transcription service.
                </small>
              </div>
              <div className="field">
                <span>{t.location}</span>
                <div className="location-row">
                  <button
                    type="button"
                    onClick={gps}
                    disabled={gpsBusy}
                    className="location-button"
                  >
                    <Navigation size={17} />
                    {gpsBusy
                      ? t.findingLocation
                      : coords
                        ? `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)} ✓`
                        : t.gps}
                  </button>
                  {coords && (
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={t.clearLocation}
                      title={t.clearLocation}
                      onClick={() => setCoords(null)}
                    >
                      <X size={17} />
                    </button>
                  )}
                </div>
              </div>
              <label>
                {t.contact}
                <input
                  type="tel"
                  autoComplete="tel"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  placeholder="+91 …"
                  maxLength={30}
                />
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  required
                />
                <span>{t.consent}</span>
              </label>
              <ErrorBox text={error} />
              <button
                disabled={
                  busy ||
                  text.length > 4000 ||
                  !consent ||
                  recording ||
                  transcribing ||
                  (!!audio && (!hasTranscript || !reviewed))
                }
                className="button primary submit"
              >
                {busy ? t.sending : t.submit}
                <ArrowRight size={19} />
              </button>
              <div className="form-note">
                <ShieldCheck size={14} /> Human coordinators review reports.
                Automated scores are advisory.
              </div>
            </form>
          )}
        </section>
      </main>
      <footer>
        Built for community preparedness.<span>AwaazSetu · Pune</span>
      </footer>
    </>
  );
}
function Track() {
  const { ticket_id } = useParams(),
    [params] = useSearchParams();
  const token = params.get("token") || "";
  const [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [refreshing, setRefreshing] = useState(false),
    [notice, setNotice] = useState("");
  const load = () => {
    setRefreshing(true);
    return api(`/track/${ticket_id}?token=${encodeURIComponent(token)}`)
      .then((d) => {
        setData(d);
        setError("");
      })
      .catch((e) => setError(e.message))
      .finally(() => setRefreshing(false));
  };
  useEffect(() => {
    load();
    // Keep the ticket current while the page is open and visible.
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 60000);
    return () => clearInterval(timer);
  }, [ticket_id, token]);
  async function clarify(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      setData(
        await api(`/track/${ticket_id}/clarify`, {
          method: "POST",
          body: JSON.stringify({ token, text }),
        }),
      );
      setText("");
      setNotice("Thank you. The location was added to your report.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PublicHeader />
      <main className="track-page">
        <Link className="subtle-link" to="/">
          ← Back to reporting
        </Link>
        <span className="eyebrow">YOUR PRIVATE REPORT</span>
        <h1>Follow your ticket.</h1>
        <ErrorBox text={error} />
        {notice && (
          <div className="success-note" role="status">
            {notice}
          </div>
        )}
        {data ? (
          <>
            <div className="card">
              <div className="section-head">
                <h2>{ticket_id}</h2>
                <span className={`badge status-${data.status}`}>
                  {nice(data.status)}
                </span>
              </div>
              <p>{data.acknowledgement}</p>
              <p className="muted">
                A ticket confirms receipt. It does not guarantee assistance.
              </p>
            </div>
            {data.needs_clarification && (
              <form className="card" onSubmit={clarify}>
                <h2>A little more detail helps.</h2>
                <p>{data.clarification_prompt}</p>
                <label>
                  Nearby landmark or address
                  <textarea
                    required
                    minLength={3}
                    maxLength={1000}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    rows={3}
                  />
                </label>
                <button className="button primary" disabled={busy}>
                  {busy ? "Sending…" : "Send clarification"}
                </button>
              </form>
            )}
            <div className="card">
              <div className="section-head">
                <h2>Updates</h2>
                <button
                  className="icon-button"
                  aria-label="Refresh updates"
                  onClick={load}
                  disabled={refreshing}
                >
                  <RefreshCw size={18} className={refreshing ? "spin" : ""} />
                </button>
              </div>
              {data.updates?.length ? (
                data.updates.map((u: any, i: number) => (
                  <div className="timeline" key={i}>
                    <span className="timeline-dot" />
                    <div>
                      <strong>{nice(u.status)}</strong>
                      <p>{u.message}</p>
                      <small>{date(u.created_at)}</small>
                    </div>
                  </div>
                ))
              ) : (
                <p className="muted">No further updates yet.</p>
              )}
            </div>
          </>
        ) : !error ? (
          <p className="muted">Loading ticket…</p>
        ) : null}
      </main>
    </>
  );
}
function Login({
  onLogin,
  expired = false,
}: {
  onLogin: () => void;
  expired?: boolean;
}) {
  const [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(
      expired ? "Your session expired. Please sign in again." : "",
    );
  async function login(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      sessionStorage.setItem("awaazsetu_token", r.token);
      onLogin();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PublicHeader />
      <main className="login-page">
        <div className="card">
          <ShieldCheck size={36} className="teal" />
          <span className="eyebrow">PRIVATE COORDINATOR ACCESS</span>
          <h1>Welcome to the coordination desk.</h1>
          <p className="muted">
            Sign in to review reports, verify incidents, and keep your community
            informed.
          </p>
          <form onSubmit={login}>
            <label>
              Coordinator password
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <ErrorBox text={error} />
            <button className="button primary submit" disabled={busy}>
              {busy ? "Signing in…" : "Enter console"}
              <ArrowRight size={18} />
            </button>
          </form>
        </div>
      </main>
    </>
  );
}
function Console() {
  const [authed, setAuthed] = useState(
    !!sessionStorage.getItem("awaazsetu_token"),
  );
  const [expired, setExpired] = useState(false);
  useEffect(() => {
    const f = () => {
      setAuthed(false);
      setExpired(true);
    };
    window.addEventListener("auth-expired", f);
    return () => window.removeEventListener("auth-expired", f);
  }, []);
  if (!authed)
    return (
      <Login
        expired={expired}
        onLogin={() => {
          setAuthed(true);
          setExpired(false);
        }}
      />
    );
  return (
    <div className="console">
      <aside className="sidebar">
        <Brand />
        <div className="nav-label">COORDINATION DESK</div>
        <nav>
          <NavLink end to="/console">
            <LayoutDashboard />
            Overview
          </NavLink>
          <NavLink to="/console/coverage">
            <ChartNoAxesCombined />
            Coverage
          </NavLink>
          <NavLink to="/console/notifications">
            <Send />
            Notifications
          </NavLink>
          <NavLink to="/console/settings">
            <Settings />
            System & settings
          </NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="private-note">
            <ShieldCheck size={20} />
            <span>
              Private workspace<small>Reports reviewed by people</small>
            </span>
          </div>
          <button
            onClick={() => {
              sessionStorage.removeItem("awaazsetu_token");
              setAuthed(false);
            }}
          >
            <LogOut size={17} /> Sign out
          </button>
        </div>
      </aside>
      <div className="console-body">
        <Drill />
        <div className="console-top">
          <span>
            <span className="live-dot" /> PUNE COMMUNITY DESK
          </span>
          <Link to="/">
            Resident report form <ArrowUpRight size={15} />
          </Link>
        </div>
        <Routes>
          <Route index element={<Overview />} />
          <Route path="coverage" element={<Coverage />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="settings" element={<System />} />
          <Route
            path="*"
            element={
              <div className="page">
                <h1>Page not found</h1>
                <Link to="/console">Go to overview</Link>
              </div>
            }
          />
        </Routes>
      </div>
    </div>
  );
}
function PageHead({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
function Overview() {
  const [items, setItems] = useState<Incident[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [selected, setSelected] = useState<Incident | null>(null),
    [q, setQ] = useState(""),
    [status, setStatus] = useState(""),
    [band, setBand] = useState(""),
    [language, setLanguage] = useState(""),
    [channel, setChannel] = useState(""),
    [updated, setUpdated] = useState("");
  async function load() {
    setLoading(true);
    setError("");
    try {
      const p = new URLSearchParams(
        Object.entries({ q, status, band, language, channel }).filter(
          ([, v]) => v,
        ),
      );
      const r = await api(`/incidents?${p}`);
      setItems(r.items);
      setUpdated(
        new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    const t = setTimeout(load, 250);
    // Poll so new reports appear without a manual refresh; skip hidden tabs.
    const poll = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 30000);
    return () => {
      clearTimeout(t);
      clearInterval(poll);
    };
  }, [q, status, band, language, channel]);
  const filtered = !!(q || status || band || language || channel);
  function clearFilters() {
    setQ("");
    setStatus("");
    setBand("");
    setLanguage("");
    setChannel("");
  }
  async function open(id: string) {
    try {
      setSelected(await api(`/incidents/${id}`));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <main className="page">
      <PageHead
        eyebrow="SITUATION OVERVIEW"
        title="A clearer picture. A faster response."
        description="Review incoming voices, confirm the situation, and coordinate the next step."
      >
        <button className="button secondary" onClick={load} disabled={loading}>
          <RefreshCw size={16} className={loading ? "spin" : ""} />
          Refresh
        </button>
      </PageHead>
      <div className="stats">
        <Stat
          label="Incidents in this view"
          value={items.length}
          icon={<MessageSquare />}
        />
        <Stat
          label="Critical priority"
          value={items.filter((i) => i.severity_band === "critical").length}
          icon={<AlertTriangle />}
          orange
        />
        <Stat
          label="Awaiting verification"
          value={items.filter((i) => i.status === "new").length}
          icon={<Clock />}
        />
        <Stat
          label="Reports represented"
          value={items.reduce((a, i) => a + i.report_count, 0)}
          icon={<Users />}
        />
      </div>
      <ErrorBox text={error} />
      <div className="overview-layout">
        <section className="card map-card">
          <div className="section-head">
            <div>
              <h2>Community incident map</h2>
              <small>Private view · Pune</small>
            </div>
            <span className="map-pill">
              <MapPin size={13} />
              {
                items.filter((i) => i.latitude != null && i.longitude != null)
                  .length
              }{" "}
              located
            </span>
          </div>
          <MapContainer
            center={[18.51, 73.85]}
            zoom={12}
            className="map"
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              referrerPolicy="strict-origin"
            />
            {items
              .filter((i) => i.latitude != null && i.longitude != null)
              .map((i) => (
                <CircleMarker
                  key={i.id}
                  center={[i.latitude!, i.longitude!]}
                  radius={i.severity_band === "critical" ? 12 : 8}
                  pathOptions={{
                    color:
                      i.severity_band === "critical"
                        ? "#d56d41"
                        : i.severity_band === "high"
                          ? "#e5a43b"
                          : "#197b74",
                    fillOpacity: 0.75,
                    weight: 2,
                  }}
                >
                  <Popup>
                    <strong>{i.ticket_id}</strong>
                    <p>{i.summary}</p>
                    <button onClick={() => open(i.id)}>Review incident</button>
                  </Popup>
                </CircleMarker>
              ))}
          </MapContainer>
          <div className="map-footer">
            <span>
              <i className="legend-dot critical" />
              Critical
            </span>
            <span>
              <i className="legend-dot high" />
              High
            </span>
            <span>
              <i className="legend-dot other" />
              Other
            </span>
            <small>Locations may be approximate. Verify before acting.</small>
          </div>
        </section>
        <section className="card desk-note">
          <Waves size={30} />
          <span className="eyebrow">KEEP PEOPLE IN THE LOOP</span>
          <h2>Every report deserves context.</h2>
          <p>
            Priority scores guide review. Read the original message, check the
            location, and use your judgment.
          </p>
          <div>
            <ShieldCheck size={16} /> Human verification required
          </div>
          <Link to="/console/notifications">
            Manage acknowledgements <ArrowUpRight size={16} />
          </Link>
        </section>
      </div>
      <section className="card queue-card">
        <div className="section-head">
          <div>
            <h2>
              Incident queue <span className="count">{items.length}</span>
            </h2>
            <small>
              {updated ? `Last refreshed ${updated}` : "Waiting for reports"}
            </small>
          </div>
          <span className="muted">Sorted by priority</span>
        </div>
        <div className="filters">
          <div className="search">
            <Search size={17} />
            <input
              aria-label="Search incidents"
              placeholder="Search ticket, landmark, or situation…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <select
            aria-label="Filter status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            {["new", "verified", "responding", "resolved", "dismissed"].map(
              (s) => (
                <option key={s}>{s}</option>
              ),
            )}
          </select>
          <select
            aria-label="Filter priority"
            value={band}
            onChange={(e) => setBand(e.target.value)}
          >
            <option value="">All priorities</option>
            {["critical", "high", "medium", "low"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            aria-label="Filter language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="">All languages</option>
            <option value="mr">Marathi</option>
            <option value="hi">Hindi</option>
            <option value="en">English</option>
          </select>
          <select
            aria-label="Filter channel"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
          >
            <option value="">All channels</option>
            {["web", "voice", "sms", "telegram"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          {filtered && (
            <button className="button ghost small" onClick={clearFilters}>
              <X size={15} />
              Clear filters
            </button>
          )}
        </div>
        {loading && !items.length ? (
          <div className="empty">Loading reports…</div>
        ) : items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>PRIORITY</th>
                  <th>INCIDENT</th>
                  <th>LOCATION</th>
                  <th>STATUS</th>
                  <th>VOICES</th>
                  <th>RECEIVED</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {[...items]
                  .sort((a, b) => b.severity_score - a.severity_score)
                  .map((i) => (
                    <tr key={i.id}>
                      <td>
                        <span className={`badge band-${i.severity_band}`}>
                          {i.severity_band} · {i.severity_score}
                        </span>
                      </td>
                      <td>
                        <button
                          className="row-title"
                          onClick={() => open(i.id)}
                        >
                          {i.summary}
                        </button>
                        <small>
                          {i.ticket_id} · {nice(i.incident_type)}
                        </small>
                      </td>
                      <td>
                        <span>{i.location_name || "Location needed"}</span>
                        <small>
                          {i.needs_clarification
                            ? "Clarification needed"
                            : i.ward || nice(i.location_method)}
                        </small>
                      </td>
                      <td>
                        <span className={`badge status-${i.status}`}>
                          {nice(i.status)}
                        </span>
                      </td>
                      <td>
                        {i.report_count}
                        <small>{i.languages?.join(" / ").toUpperCase()}</small>
                      </td>
                      <td className="muted">{date(i.created_at)}</td>
                      <td>
                        <button
                          className="icon-button"
                          aria-label={`Review ${i.ticket_id}`}
                          onClick={() => open(i.id)}
                        >
                          <ArrowUpRight size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">
            <MessageSquare size={30} />
            <h3>No incidents in this view</h3>
            <p>
              {filtered
                ? "No incidents match these filters."
                : "New resident reports will appear here. Submit a report or load drill examples to get started."}
            </p>
            {filtered && (
              <button className="button secondary small" onClick={clearFilters}>
                Clear filters
              </button>
            )}
          </div>
        )}
      </section>
      {selected && (
        <Detail
          incident={selected}
          items={items}
          onClose={() => setSelected(null)}
          onChange={(i) => {
            setSelected((current) => (current?.id === i.id ? i : current));
            load();
          }}
        />
      )}
    </main>
  );
}
function Stat({
  label,
  value,
  icon,
  orange = false,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  orange?: boolean;
}) {
  return (
    <div className="stat">
      <span className={`stat-icon ${orange ? "orange" : ""}`}>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
function Detail({
  incident: i,
  items,
  onClose,
  onChange,
}: {
  incident: Incident;
  items: Incident[];
  onClose: () => void;
  onChange: (i: Incident) => void;
}) {
  const [notes, setNotes] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [source, setSource] = useState("");
  const drawerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const bodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    drawerRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const nodes = drawerRef.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input,textarea,select,a[href]",
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = bodyOverflow;
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, []);
  const closed = i.status === "resolved" || i.status === "dismissed";
  async function status(s: string | null) {
    if (
      s === "dismissed" &&
      !window.confirm(
        `Dismiss ${i.ticket_id}? Reporters will be told it was closed after review.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      onChange(
        await api(`/incidents/${i.id}`, {
          method: "PATCH",
          body: JSON.stringify(s ? { status: s, notes } : { notes }),
        }),
      );
      setNotes("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function merge() {
    const other = items.find((a) => a.id === source);
    if (
      !window.confirm(
        `Merge ${other?.ticket_id ?? "the selected incident"} into ${i.ticket_id}? The other incident will be removed and its reports moved here.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      onChange(
        await api(`/incidents/${i.id}/merge`, {
          method: "POST",
          body: JSON.stringify({ source_id: source, reason: notes }),
        }),
      );
      setSource("");
      setNotes("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <section
        ref={drawerRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Incident detail"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="section-head">
          <span className="eyebrow">{i.ticket_id}</span>
          <button
            aria-label="Close detail"
            className="icon-button"
            onClick={onClose}
          >
            <X />
          </button>
        </div>
        <div className="status-line">
          <span className={`badge status-${i.status}`}>{nice(i.status)}</span>
          <span className={`badge band-${i.severity_band}`}>
            {i.severity_band} priority · {i.severity_score}/100
          </span>
        </div>
        <h2>{i.summary}</h2>
        <div className="detail-meta">
          <MapPin size={17} />
          <span>
            {i.location_name || "Unknown location"}
            <small>
              {nice(i.location_method)} ·{" "}
              {Math.round(i.location_confidence * 100)}% confidence
            </small>
          </span>
        </div>
        {i.needs_clarification && (
          <p className="warning">
            Location clarification needed. Do not assume an exact address.
          </p>
        )}
        <hr />
        <h3>Why this priority?</h3>
        <p className="muted">
          Advisory rule score; thresholds have not been field validated.
        </p>
        {i.severity_reasons?.map((r, n) => (
          <div className="reason" key={n}>
            <span>{r.label}</span>
            <strong>+{r.points}</strong>
          </div>
        ))}
        <hr />
        <h3>Coordinator action</h3>
        <label>
          Notes
          <textarea
            rows={3}
            maxLength={2000}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Record what you verified or the next action…"
          />
        </label>
        <div className="note-actions">
          <button
            className="button ghost small"
            disabled={busy || !notes.trim()}
            onClick={() => status(null)}
          >
            Save note only
          </button>
        </div>
        <div className="action-grid">
          {["verified", "responding", "resolved", "dismissed"].map((s) => (
            <button
              className={`button ${s === "verified" ? "primary" : "secondary"}`}
              disabled={busy || i.status === s}
              key={s}
              onClick={() => status(s)}
            >
              {s === "verified" ? (
                <ShieldCheck size={16} />
              ) : (
                <Check size={16} />
              )}{" "}
              {nice(s)}
            </button>
          ))}
        </div>
        <ErrorBox text={error} />
        <hr />
        <h3>Original voices · {i.report_count}</h3>
        {i.reports?.map((r) => (
          <article className="source-report" key={r.id}>
            <div>
              <span className="badge">
                {r.language?.toUpperCase()} · {r.channel}
              </span>
              {(r.synthetic || r.is_synthetic || r.fields?.synthetic) && (
                <span className="badge band-high">Synthetic drill report</span>
              )}
              <small>{date(r.created_at)}</small>
            </div>
            <p>{r.text}</p>
            <small>
              Extraction:{" "}
              {nice(r.extraction_method || r.fields?.extraction_method)}
            </small>
          </article>
        ))}
        <hr />
        <h3>Combine a duplicate</h3>
        <p className="muted">
          Automatic merging checks incident type, distance within 500 m, and
          time within 3 hours. A coordinator merge is an explicit override:
          confirm both reports describe the same incident. Source reports are
          kept. Add a review note explaining the merge before proceeding.
        </p>
        {closed && (
          <p className="warning">
            This incident is closed. Reopen it as verified or responding before
            merging.
          </p>
        )}
        <select
          aria-label="Select duplicate to merge"
          value={source}
          disabled={closed}
          onChange={(e) => setSource(e.target.value)}
        >
          <option value="">Select a source incident…</option>
          {items
            .filter((a) => a.id !== i.id)
            .map((a) => (
              <option value={a.id} key={a.id}>
                {a.ticket_id} — {a.summary}
              </option>
            ))}
        </select>
        <button
          disabled={closed || !source || busy || notes.trim().length < 5}
          className="button secondary"
          onClick={merge}
        >
          Merge into this incident
        </button>
        {source && notes.trim().length < 5 && (
          <small className="muted">
            Add a note of at least 5 characters above to explain the merge.
          </small>
        )}
        <hr />
        <h3>Activity</h3>
        {i.history?.map((h, n) => (
          <div className="timeline" key={n}>
            <span className="timeline-dot" />
            <div>
              <strong>{nice(h.status)}</strong>
              <p>{h.notes || "Status updated"}</p>
              <small>{date(h.created_at)}</small>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
function Coverage() {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api("/coverage")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <main className="page">
      <PageHead
        eyebrow="LISTENING EQUITABLY"
        title="Who are we hearing from?"
        description="Understand reporting patterns. Find areas that may need a closer look."
      />
      <ErrorBox text={error} />
      {data ? (
        <>
          <div className="stats three">
            <Stat
              label="Total reports"
              value={data.total_reports}
              icon={<MessageSquare />}
            />
            <Stat
              label="Distinct incidents"
              value={data.total_incidents}
              icon={<MapPin />}
            />
            <Stat
              label="Unique reporters"
              value={data.unique_reporters}
              icon={<Users />}
            />
          </div>
          <div className="chart-grid">
            {[
              ["Reports by language", data.by_language],
              ["Reports by channel", data.by_channel],
            ].map(([title, rows]) => (
              <section className="card" key={title as string}>
                <h2>{title as string}</h2>
                {(rows as any[])?.length ? (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart
                      data={rows as any[]}
                      margin={{ top: 20, right: 20, left: -20, bottom: 5 }}
                    >
                      <XAxis dataKey="label" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar
                        dataKey="count"
                        fill="#197b74"
                        radius={[5, 5, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="empty">No reports yet.</div>
                )}
              </section>
            ))}
          </div>
          <section className="card">
            <h2>Ward coverage</h2>
            <p className="muted">{data.baseline_note}</p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>WARD / AREA</th>
                    <th>REPORTS</th>
                    <th>EXPECTED BASELINE</th>
                    <th>GAP INDEX</th>
                    <th>BASELINE SOURCE</th>
                  </tr>
                </thead>
                <tbody>
                  {data.wards?.map((w: any) => (
                    <tr key={w.ward}>
                      <td>{w.ward || "Unassigned"}</td>
                      <td>{w.reports}</td>
                      <td>{w.expected_reports ?? "Not configured"}</td>
                      <td>
                        {w.gap_index != null
                          ? Number(w.gap_index).toFixed(2)
                          : "—"}
                      </td>
                      <td>{w.baseline || "Not configured"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="info-note">
              Low report counts alone do not establish a coverage gap. Interpret
              these figures alongside local conditions and an agreed baseline.
            </div>
          </section>
        </>
      ) : !error ? (
        <div className="empty">Loading coverage…</div>
      ) : null}
    </main>
  );
}
function Notifications() {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [ward, setWard] = useState(""),
    [language, setLanguage] = useState("mr"),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [wards, setWards] = useState<string[]>([]);
  const load = () =>
    api("/outbox")
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
    // Suggest known ward names; alerts only reach contacts whose ward matches exactly.
    api("/coverage")
      .then((c) =>
        setWards(
          (c.wards || [])
            .map((w: any) => w.ward)
            .filter((w: string) => w && w !== "Unlocated"),
        ),
      )
      .catch(() => {});
  }, []);
  async function retry() {
    setBusy(true);
    setError("");
    try {
      const r = await api("/outbox/retry", { method: "POST" });
      setNotice(
        r.note ??
          `Processed ${r.processed}; sent ${r.sent}; failed ${r.failed}.`,
      );
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function alert(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api("/alerts", {
        method: "POST",
        body: JSON.stringify({ ward, language, message }),
      });
      setNotice(
        `Alert queued for ${r.queued} opted-in recipients.` +
          (r.queued
            ? ""
            : " Recipients must have joined alerts for this exact ward and language."),
      );
      setMessage("");
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="page">
      <PageHead
        eyebrow="COMMUNITY COMMUNICATION"
        title="Keep the connection open."
        description="Review delivery, retry queued messages, and share area updates."
      />
      <ErrorBox text={error} />
      {notice && (
        <div className="success-note" role="status">
          {notice}
        </div>
      )}
      <div className="notification-layout">
        <section className="card">
          <div className="section-head">
            <h2>
              Message outbox <span className="count">{data?.total ?? 0}</span>
            </h2>
            <button
              className="button secondary"
              disabled={busy}
              onClick={retry}
            >
              <RefreshCw size={16} className={busy ? "spin" : ""} />
              Retry pending
            </button>
          </div>
          <p className="muted">
            Delivery depends on configured gateways. A queued message is not a
            delivery confirmation.
          </p>
          {data?.items?.length ? (
            <div className="outbox">
              {data.items.map((m: any) => (
                <article key={m.id}>
                  <div className="section-head">
                    <span className="badge">
                      {m.channel} · {m.language?.toUpperCase()}
                    </span>
                    <span className={`badge status-${m.status}`}>
                      {nice(m.status)}
                    </span>
                  </div>
                  <p>{m.message}</p>
                  <small>
                    {m.ticket_id || "Area alert"} · {date(m.created_at)} ·{" "}
                    {m.attempts} attempts
                  </small>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty">
              <Send size={28} />
              <h3>{data ? "No messages yet" : "Loading outbox…"}</h3>
            </div>
          )}
        </section>
        <form className="card alert-form" onSubmit={alert}>
          <span className="eyebrow">AREA UPDATE</span>
          <h2>Send a community alert</h2>
          <p className="muted">
            Only opted-in recipients in the selected ward receive this message.
          </p>
          <label>
            Ward / area
            <input
              required
              maxLength={100}
              value={ward}
              list="known-wards"
              onChange={(e) => setWard(e.target.value)}
              placeholder="Start typing to pick a known ward"
            />
            <datalist id="known-wards">
              {wards.map((w) => (
                <option key={w} value={w} />
              ))}
            </datalist>
          </label>
          <label>
            Language
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="mr">Marathi</option>
              <option value="hi">Hindi</option>
              <option value="en">English</option>
            </select>
          </label>
          <label>
            Message
            <textarea
              required
              minLength={3}
              rows={5}
              maxLength={1000}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Write a clear, verified update…"
            />
          </label>
          <small className="char-count">{message.length} / 1000</small>
          <button className="button primary submit" disabled={busy}>
            <Send size={16} />
            {busy ? "Queuing…" : "Queue alert"}
          </button>
        </form>
      </div>
    </main>
  );
}
function System() {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/settings")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  async function seed() {
    setBusy(true);
    setError("");
    try {
      const r = await api("/demo/seed", { method: "POST" });
      setNotice(
        `Drill dataset ready: ${r.reports} reports and ${r.incidents} incidents.`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    setError("");
    try {
      const r = await fetch(`${base}/api/export/reports.csv`, {
        headers: {
          Authorization: `Bearer ${sessionStorage.getItem("awaazsetu_token")}`,
        },
      });
      if (!r.ok) throw new Error(`Export failed (${r.status})`);
      const u = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = u;
      a.download = "awaazsetu-reports.csv";
      a.click();
      // Revoking synchronously can cancel the download in some browsers.
      setTimeout(() => URL.revokeObjectURL(u), 1000);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <main className="page">
      <PageHead
        eyebrow="SYSTEM READINESS"
        title="Know what is connected."
        description="Integration status, drill data, and reporting tools for your desk."
      />
      <ErrorBox text={error} />
      {notice && <div className="success-note">{notice}</div>}
      {data ? (
        <>
          <div className="card">
            <div className="section-head">
              <h2>Integrations</h2>
              <span className="badge">
                {data.demo ? "Drill mode" : "Coordination mode"}
              </span>
            </div>
            <div className="integrations">
              {data.integrations?.map((i: any) => (
                <div key={i.name}>
                  <div>
                    <strong>{nice(i.name)}</strong>
                    <p>{i.description}</p>
                  </div>
                  <span
                    className={`badge ${i.configured ? "status-verified" : "status-new"}`}
                  >
                    {i.configured ? "Configured" : "Not configured"}
                  </span>
                </div>
              ))}
            </div>
            <p className="muted">
              Configured means credentials are present. Verify delivery and
              accuracy through a supervised drill.
            </p>
          </div>
          <div className="chart-grid">
            <section className="card">
              <MapPin className="teal" />
              <h2>Location reference</h2>
              <p>
                <strong>{data.gazetteer_count}</strong> landmarks in the
                gazetteer.
              </p>
              <p className="muted">
                Coordinates may be approximate or unverified. Unknown landmarks
                prompt clarification instead of an assumed location.
              </p>
            </section>
            <section className="card">
              <ChartNoAxesCombined className="teal" />
              <h2>Coverage baseline</h2>
              <p className="muted">{data.baseline_note}</p>
              <Link className="subtle-link" to="/console/coverage">
                View coverage <ArrowUpRight size={15} />
              </Link>
            </section>
          </div>
          <div className="card">
            <h2>Desk tools</h2>
            <div className="button-row">
              <button className="button secondary" onClick={download}>
                <Download size={17} />
                Export reports CSV
              </button>
              {data.demo && (
                <button
                  className="button secondary"
                  onClick={seed}
                  disabled={busy}
                >
                  <Users size={17} />
                  {busy ? "Preparing…" : "Load drill examples"}
                </button>
              )}
            </div>
            <p className="muted">
              Exports contain report text and should stay within the
              coordination team. Drill examples are synthetic and explicitly
              labelled.
            </p>
          </div>
        </>
      ) : !error ? (
        <div className="empty">Loading system status…</div>
      ) : null}
    </main>
  );
}
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Resident />} />
      <Route path="/track/:ticket_id" element={<Track />} />
      <Route path="/console/*" element={<Console />} />
      <Route
        path="*"
        element={
          <>
            <PublicHeader />
            <main className="track-page">
              <h1>Page not found.</h1>
              <Link className="button primary" to="/">
                Go to report form
              </Link>
            </main>
          </>
        }
      />
    </Routes>
  );
}
