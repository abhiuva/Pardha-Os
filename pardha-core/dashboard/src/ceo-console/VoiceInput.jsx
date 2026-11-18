import { Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export function VoiceInput({ disabled, onTranscript }) {
  const recognitionRef = useRef(null);
  const [state, setState] = useState("idle");
  const [error, setError] = useState("");

  useEffect(() => () => recognitionRef.current?.abort?.(), []);

  async function start() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setError("");
    if (!Recognition || !navigator.mediaDevices?.getUserMedia) {
      setError("Voice capture is unavailable in this browser. Text input remains available.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
    } catch (nextError) {
      setError(nextError?.name === "NotAllowedError" ? "Microphone permission was denied." : "Microphone access failed.");
      return;
    }
    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onstart = () => setState("listening");
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results).map((result) => result[0].transcript).join(" ").trim();
      onTranscript(transcript);
    };
    recognition.onerror = (event) => {
      setError(`Voice capture failed: ${event.error}`);
      setState("idle");
    };
    recognition.onend = () => setState("idle");
    recognitionRef.current = recognition;
    recognition.start();
  }

  function stop() {
    recognitionRef.current?.stop?.();
    setState("idle");
  }

  return (
    <div>
      <button
        type="button"
        onClick={state === "listening" ? stop : start}
        disabled={disabled}
        aria-pressed={state === "listening"}
        className="inline-flex h-11 items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 text-sm font-semibold text-slate-200 disabled:opacity-40"
      >
        {state === "listening" ? <Square size={16} /> : <Mic size={17} />}
        {state === "listening" ? "Stop listening" : "Use voice"}
      </button>
      {error && <p role="alert" className="mt-2 text-xs text-amber-300">{error}</p>}
    </div>
  );
}
