const apiStatus = document.querySelector("#apiStatus");
const micButton = document.querySelector("#micButton");
const micState = document.querySelector("#micState");
const micMeter = document.querySelector(".mic-meter");
const vadState = document.querySelector("#vadState");
const turnState = document.querySelector("#turnState");
const latencyState = document.querySelector("#latencyState");
const cefrState = document.querySelector("#cefrState");
const scenario = document.querySelector("#scenario");
const utterance = document.querySelector("#utterance");
const sendButton = document.querySelector("#sendButton");
const clearButton = document.querySelector("#clearButton");
const sampleButton = document.querySelector("#sampleButton");
const aiReply = document.querySelector("#aiReply");
const correction = document.querySelector("#correction");
const feedbackItems = document.querySelector("#feedbackItems");
const meterBars = Array.from(document.querySelectorAll(".mic-meter span"));

let audioContext;
let analyser;
let micStream;
let animationFrame;

async function checkApi() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    apiStatus.textContent = "API online";
    apiStatus.classList.add("ok");
    apiStatus.classList.remove("error");
  } catch (error) {
    apiStatus.textContent = "API offline";
    apiStatus.classList.add("error");
    apiStatus.classList.remove("ok");
  }
}

function setMeter(level) {
  const speaking = level > 0.08;
  vadState.textContent = speaking ? "Speech" : "Listening";
  micMeter.classList.toggle("active", speaking);
  meterBars.forEach((bar, index) => {
    const weight = (index + 1) / meterBars.length;
    const height = Math.max(10, Math.round((level * 92 + weight * 18) * 100) / 10);
    bar.style.height = `${Math.min(72, height)}px`;
  });
}

function renderAudioLevel() {
  const data = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(data);
  let total = 0;
  for (const value of data) {
    const centered = (value - 128) / 128;
    total += centered * centered;
  }
  setMeter(Math.sqrt(total / data.length));
  animationFrame = requestAnimationFrame(renderAudioLevel);
}

async function startMic() {
  micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioContext = new AudioContext();
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 512;
  const source = audioContext.createMediaStreamSource(micStream);
  source.connect(analyser);
  micButton.textContent = "Stop mic";
  micState.textContent = "Microphone active";
  turnState.textContent = "Listening";
  renderAudioLevel();
}

function stopMic() {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame);
  }
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
  }
  if (audioContext) {
    audioContext.close();
  }
  audioContext = undefined;
  analyser = undefined;
  micStream = undefined;
  setMeter(0);
  micButton.textContent = "Start mic";
  micState.textContent = "Microphone idle";
  vadState.textContent = "Idle";
  turnState.textContent = "Ready";
}

async function toggleMic() {
  if (micStream) {
    stopMic();
    return;
  }

  try {
    await startMic();
  } catch (error) {
    micState.textContent = "Microphone permission denied";
    vadState.textContent = "Blocked";
  }
}

function renderFeedback(items) {
  feedbackItems.innerHTML = "";
  items.forEach((item) => {
    const element = document.createElement("li");
    element.textContent = `${item.type}: ${item.original} -> ${item.suggestion}. ${item.reason}`;
    feedbackItems.appendChild(element);
  });
}

async function sendTurn() {
  const text = utterance.value.trim();
  sendButton.disabled = true;
  turnState.textContent = "Processing";
  aiReply.textContent = "Generating feedback...";

  try {
    const response = await fetch("/api/conversation/mock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, scenario: scenario.value }),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const result = await response.json();
    aiReply.textContent = result.reply;
    correction.textContent = result.corrected;
    latencyState.textContent = `${result.metrics.mockLatencyMs} ms`;
    cefrState.textContent = result.metrics.cefrEstimate;
    turnState.textContent = "Ready";
    renderFeedback(result.feedback);
  } catch (error) {
    aiReply.textContent = "The local API is not available.";
    turnState.textContent = "Error";
  } finally {
    sendButton.disabled = false;
  }
}

function useSample() {
  utterance.value =
    "I am agree with this idea because it help me learn faster and discuss about problems with classmates.";
  utterance.focus();
}

function clearTurn() {
  utterance.value = "";
  aiReply.textContent = "Waiting for your first practice turn.";
  correction.textContent = "No correction yet.";
  feedbackItems.innerHTML = "<li>Submit a turn to generate speaking feedback.</li>";
  latencyState.textContent = "-- ms";
  cefrState.textContent = "--";
  turnState.textContent = "Ready";
}

micButton.addEventListener("click", toggleMic);
sendButton.addEventListener("click", sendTurn);
sampleButton.addEventListener("click", useSample);
clearButton.addEventListener("click", clearTurn);

checkApi();
