"""AwazSetu — the interface language pack.

One flat catalogue, four languages, used by BOTH sides of the app:

    render_template(..., T=i18n.pack(lang))     # Jinja:  {{ T.chat_ask }}
    const T = {{ T|tojson }};                   # browser: T.chat_ask

Keeping server strings and browser strings in the same dict is deliberate. The
previous UI had English baked into the JavaScript — "Uploading…", "Voice error",
the voiceover hints — so a Hindi user got a Hindi page with English status
messages the moment anything actually happened. A single pack shipped to the page
makes that structurally impossible: a string in the catalogue is translated
everywhere, and a string missing from it is missing everywhere and shows up at
once.

Fallback is to English, never to the key: a missing Odia string reads as English,
which is usable, rather than as `pl_dub_missing`, which is not.
"""
from __future__ import annotations

# Interface languages. Deliberately the same four as the CONTENT languages in
# langs.py — someone who reads Odia subtitles should not have to drive the app in
# English. Odia has no speech recognition (see langs.py), but that limits the
# microphone only; every button, label, subtitle, voiceover and answer works.
UI_LANGS = ("en", "hi", "mr", "or")
DEFAULT_UI = "en"

# Native names for the picker, always in the language's own script so it can be
# recognised by someone who can read nothing else on the screen.
UI_NAMES = {"en": "English", "hi": "हिंदी", "mr": "मराठी", "or": "ଓଡ଼ିଆ"}
UI_SUBTITLES = {"en": "English", "hi": "Hindi", "mr": "Marathi", "or": "Odia"}

S: dict[str, dict[str, str]] = {

    # ---------------- shared chrome ----------------
    "app_tagline": {
        "en": "offline video translate · voiceover · chat",
        "hi": "ऑफ़लाइन वीडियो अनुवाद · आवाज़ · चैट",
        "mr": "ऑफलाइन व्हिडिओ भाषांतर · आवाज · चॅट",
        "or": "ଅଫଲାଇନ ଭିଡିଓ ଅନୁବାଦ · ସ୍ୱର · ଚାଟ୍",
    },
    "nav_garden": {
        "en": "Model Garden", "hi": "मॉडल गार्डन",
        "mr": "मॉडेल गार्डन", "or": "ମଡେଲ ଗାର୍ଡେନ",
    },
    "nav_settings": {
        "en": "Settings", "hi": "सेटिंग्स", "mr": "सेटिंग्ज", "or": "ସେଟିଂସ",
    },
    "nav_home": {
        "en": "Home", "hi": "होम", "mr": "होम", "or": "ହୋମ",
    },
    "nav_library": {
        "en": "Library", "hi": "लाइब्रेरी", "mr": "लायब्ररी", "or": "ଲାଇବ୍ରେରୀ",
    },
    "badge_offline": {
        "en": "100% offline", "hi": "100% ऑफ़लाइन",
        "mr": "100% ऑफलाइन", "or": "100% ଅଫଲାଇନ",
    },

    # ---------------- language picker ----------------
    "lang_title": {
        "en": "Choose your language",
        "hi": "अपनी भाषा चुनें",
        "mr": "तुमची भाषा निवडा",
        "or": "ଆପଣଙ୍କ ଭାଷା ବାଛନ୍ତୁ",
    },
    "lang_sub": {
        "en": "Buttons, subtitles, voiceovers and answers will all use this language.",
        "hi": "बटन, सबटाइटल, आवाज़ और उत्तर — सब इसी भाषा में होंगे।",
        "mr": "बटणे, सबटायटल, आवाज आणि उत्तरे — सर्व याच भाषेत असतील.",
        "or": "ବଟନ, ସବଟାଇଟଲ, ସ୍ୱର ଏବଂ ଉତ୍ତର — ସବୁ ଏହି ଭାଷାରେ ହେବ।",
    },
    "lang_continue": {
        "en": "Continue", "hi": "आगे बढ़ें", "mr": "पुढे जा", "or": "ଆଗକୁ ଯାଆନ୍ତୁ",
    },
    "lang_hint": {
        "en": "You can change this any time in Settings.",
        "hi": "इसे कभी भी सेटिंग्स में बदल सकते हैं।",
        "mr": "हे कधीही सेटिंग्जमध्ये बदलता येते.",
        "or": "ଏହା ଯେକୌଣସି ସମୟରେ ସେଟିଂସରେ ବଦଳାଇପାରିବେ।",
    },

    # ---------------- home ----------------
    "home_add": {
        "en": "Add a video", "hi": "वीडियो जोड़ें",
        "mr": "व्हिडिओ जोडा", "or": "ଭିଡିଓ ଯୋଡ଼ନ୍ତୁ",
    },
    "home_drop": {
        "en": "Drop a video or audio file here, or click to choose",
        "hi": "यहाँ वीडियो या ऑडियो फ़ाइल छोड़ें, या चुनने के लिए क्लिक करें",
        "mr": "इथे व्हिडिओ किंवा ऑडिओ फाइल टाका, किंवा निवडण्यासाठी क्लिक करा",
        "or": "ଏଠାରେ ଭିଡିଓ କିମ୍ବା ଅଡିଓ ଫାଇଲ ଛାଡ଼ନ୍ତୁ, କିମ୍ବା ବାଛିବାକୁ କ୍ଲିକ କରନ୍ତୁ",
    },
    "home_drop_sub": {
        "en": "Hindi / Marathi / English / Odia · processed entirely on this machine",
        "hi": "हिंदी / मराठी / अंग्रेज़ी / ओड़िया · पूरी प्रक्रिया इसी मशीन पर",
        "mr": "हिंदी / मराठी / इंग्रजी / ओडिया · संपूर्ण प्रक्रिया याच मशीनवर",
        "or": "ହିନ୍ଦୀ / ମରାଠୀ / ଇଂରାଜୀ / ଓଡ଼ିଆ · ସମ୍ପୂର୍ଣ୍ଣ ପ୍ରକ୍ରିୟା ଏହି ମେସିନରେ",
    },
    "home_search": {
        "en": "Search across your library",
        "hi": "अपनी लाइब्रेरी में खोजें",
        "mr": "तुमच्या लायब्ररीत शोधा",
        "or": "ଆପଣଙ୍କ ଲାଇବ୍ରେରୀରେ ଖୋଜନ୍ତୁ",
    },
    "home_search_ph": {
        "en": "Find a moment across all processed videos…",
        "hi": "सभी वीडियो में कोई पल खोजें…",
        "mr": "सर्व व्हिडिओंमध्ये एखादा क्षण शोधा…",
        "or": "ସମସ୍ତ ଭିଡିଓରେ ଏକ ମୁହୂର୍ତ୍ତ ଖୋଜନ୍ତୁ…",
    },
    "home_processed": {
        "en": "Your videos", "hi": "आपके वीडियो",
        "mr": "तुमचे व्हिडिओ", "or": "ଆପଣଙ୍କ ଭିଡିଓ",
    },
    "home_empty": {
        "en": "No videos yet — add one above.",
        "hi": "अभी कोई वीडियो नहीं — ऊपर जोड़ें।",
        "mr": "अजून व्हिडिओ नाहीत — वर जोडा.",
        "or": "ଏପର୍ଯ୍ୟନ୍ତ କୌଣସି ଭିଡିଓ ନାହିଁ — ଉପରେ ଯୋଡ଼ନ୍ତୁ।",
    },
    "home_uploading": {
        "en": "Uploading…", "hi": "अपलोड हो रहा है…",
        "mr": "अपलोड होत आहे…", "or": "ଅପଲୋଡ ହେଉଛି…",
    },
    "home_done": {
        "en": "Done — opening…", "hi": "पूरा हुआ — खुल रहा है…",
        "mr": "पूर्ण झाले — उघडत आहे…", "or": "ସମ୍ପୂର୍ଣ୍ଣ — ଖୋଲୁଛି…",
    },
    "home_processing": {
        "en": "processing", "hi": "प्रक्रिया जारी",
        "mr": "प्रक्रिया सुरू", "or": "ପ୍ରକ୍ରିୟା ଚାଲିଛି",
    },
    "home_nomatch": {
        "en": "No matches.", "hi": "कोई परिणाम नहीं।",
        "mr": "काहीही सापडले नाही.", "or": "କିଛି ମିଳିଲା ନାହିଁ।",
    },
    "home_error": {
        "en": "Error", "hi": "त्रुटि", "mr": "त्रुटी", "or": "ତ୍ରୁଟି",
    },

    # ---------------- player ----------------
    "pl_subs": {
        "en": "Subtitles — switch any time",
        "hi": "सबटाइटल — कभी भी बदलें",
        "mr": "सबटायटल — कधीही बदला",
        "or": "ସବଟାଇଟଲ — ଯେକୌଣସି ସମୟରେ ବଦଳାନ୍ତୁ",
    },
    "pl_off": {"en": "Off", "hi": "बंद", "mr": "बंद", "or": "ବନ୍ଦ"},
    "pl_dub": {
        "en": "Voiceover — hear it in another language",
        "hi": "आवाज़ — दूसरी भाषा में सुनें",
        "mr": "आवाज — दुसऱ्या भाषेत ऐका",
        "or": "ସ୍ୱର — ଅନ୍ୟ ଭାଷାରେ ଶୁଣନ୍ତୁ",
    },
    "pl_original": {"en": "Original", "hi": "मूल", "mr": "मूळ", "or": "ମୂଳ"},
    "pl_dub_hint": {
        "en": "Voiceovers are made when the video is saved — playback is instant.",
        "hi": "आवाज़ वीडियो सहेजते समय ही बन जाती है — तुरंत चलती है।",
        "mr": "आवाज व्हिडिओ जतन करतानाच तयार होते — लगेच वाजते.",
        "or": "ଭିଡିଓ ସେଭ କରିବା ସମୟରେ ସ୍ୱର ତିଆରି ହୁଏ — ସଙ୍ଗେ ସଙ୍ଗେ ବାଜେ।",
    },
    "pl_dub_orig": {
        "en": "Original audio.", "hi": "मूल ऑडियो।",
        "mr": "मूळ ऑडिओ.", "or": "ମୂଳ ଅଡିଓ।",
    },
    "pl_dub_missing": {
        "en": "This voiceover was not made for this video. Use Re-process to build it.",
        "hi": "इस वीडियो के लिए यह आवाज़ नहीं बनी है। इसे बनाने के लिए “दोबारा प्रक्रिया” चुनें।",
        "mr": "या व्हिडिओसाठी ही आवाज तयार झालेली नाही. तयार करण्यासाठी “पुन्हा प्रक्रिया” वापरा.",
        "or": "ଏହି ଭିଡିଓ ପାଇଁ ଏହି ସ୍ୱର ତିଆରି ହୋଇନାହିଁ। ତିଆରି କରିବାକୁ “ପୁନଃ ପ୍ରକ୍ରିୟା” ବ୍ୟବହାର କରନ୍ତୁ।",
    },
    "pl_dub_playing": {
        "en": "Playing the voiceover — original audio muted. Click Original to go back.",
        "hi": "आवाज़ चल रही है — मूल ऑडियो बंद है। वापस जाने के लिए “मूल” दबाएँ।",
        "mr": "आवाज सुरू आहे — मूळ ऑडिओ बंद आहे. परत जाण्यासाठी “मूळ” दाबा.",
        "or": "ସ୍ୱର ବାଜୁଛି — ମୂଳ ଅଡିଓ ବନ୍ଦ। ଫେରିବାକୁ “ମୂଳ” ଦବାନ୍ତୁ।",
    },
    "pl_download": {
        "en": "Download", "hi": "डाउनलोड", "mr": "डाउनलोड", "or": "ଡାଉନଲୋଡ",
    },
    "pl_transcript": {
        "en": "Transcript", "hi": "ट्रांसक्रिप्ट",
        "mr": "ट्रान्सक्रिप्ट", "or": "ଟ୍ରାନ୍ସକ୍ରିପ୍ଟ",
    },
    "pl_bundle": {
        "en": "Bundle .mkv", "hi": "बंडल .mkv", "mr": "बंडल .mkv", "or": "ବଣ୍ଡଲ .mkv",
    },
    "pl_reprocess": {
        "en": "Re-process", "hi": "दोबारा प्रक्रिया",
        "mr": "पुन्हा प्रक्रिया", "or": "ପୁନଃ ପ୍ରକ୍ରିୟା",
    },
    "pl_reprocess_confirm": {
        "en": "Re-process this video with the current settings? This re-runs transcription and translation.",
        "hi": "क्या इस वीडियो को मौजूदा सेटिंग्स के साथ दोबारा प्रोसेस करें? ट्रांसक्रिप्शन और अनुवाद फिर से होंगे।",
        "mr": "हा व्हिडिओ सध्याच्या सेटिंग्जसह पुन्हा प्रोसेस करायचा? ट्रान्सक्रिप्शन आणि भाषांतर पुन्हा होईल.",
        "or": "ଏହି ଭିଡିଓକୁ ବର୍ତ୍ତମାନର ସେଟିଂସ ସହ ପୁନଃ ପ୍ରକ୍ରିୟା କରିବେ? ଟ୍ରାନ୍ସକ୍ରିପସନ ଓ ଅନୁବାଦ ପୁଣି ହେବ।",
    },
    "pl_reprocess_started": {
        "en": "Re-processing started — refresh in a minute, or watch the Home page.",
        "hi": "दोबारा प्रक्रिया शुरू — एक मिनट बाद पेज ताज़ा करें, या होम पेज देखें।",
        "mr": "पुन्हा प्रक्रिया सुरू — एका मिनिटात पेज रिफ्रेश करा, किंवा होम पेज पहा.",
        "or": "ପୁନଃ ପ୍ରକ୍ରିୟା ଆରମ୍ଭ — ଏକ ମିନିଟ ପରେ ପେଜ ରିଫ୍ରେସ କରନ୍ତୁ, କିମ୍ବା ହୋମ ପେଜ ଦେଖନ୍ତୁ।",
    },
    "pl_audio_sub": {
        "en": "Audio · subtitles below", "hi": "ऑडियो · सबटाइटल नीचे",
        "mr": "ऑडिओ · सबटायटल खाली", "or": "ଅଡିଓ · ସବଟାଇଟଲ ତଳେ",
    },

    # ---------------- chat ----------------
    "chat_title": {
        "en": "Ask this video", "hi": "इस वीडियो से पूछें",
        "mr": "या व्हिडिओला विचारा", "or": "ଏହି ଭିଡିଓକୁ ପଚାରନ୍ତୁ",
    },
    "chat_answer_in": {
        "en": "Answer in:", "hi": "उत्तर की भाषा:",
        "mr": "उत्तराची भाषा:", "or": "ଉତ୍ତରର ଭାଷା:",
    },
    "chat_welcome": {
        "en": "Ask me anything about this video. I answer only from what is said in it, and only on this machine.",
        "hi": "इस वीडियो के बारे में कुछ भी पूछें। मैं केवल उसी में कही गई बातों से उत्तर देता हूँ, और सब कुछ इसी मशीन पर होता है।",
        "mr": "या व्हिडिओबद्दल काहीही विचारा. मी फक्त त्यात सांगितलेल्या गोष्टींवरून उत्तर देतो, आणि सर्व काही याच मशीनवर होते.",
        "or": "ଏହି ଭିଡିଓ ବିଷୟରେ ଯାହା ବି ପଚାରନ୍ତୁ। ମୁଁ କେବଳ ସେଥିରେ କୁହାଯାଇଥିବା କଥାରୁ ଉତ୍ତର ଦିଏ, ଏବଂ ସବୁ ଏହି ମେସିନରେ ହୁଏ।",
    },
    "chat_ph": {
        "en": "Type, or tap the microphone to speak…",
        "hi": "लिखें, या बोलने के लिए माइक दबाएँ…",
        "mr": "टाइप करा, किंवा बोलण्यासाठी माइक दाबा…",
        "or": "ଟାଇପ କରନ୍ତୁ, କିମ୍ବା କହିବାକୁ ମାଇକ ଦବାନ୍ତୁ…",
    },
    "chat_ask": {
        "en": "Ask", "hi": "पूछें", "mr": "विचारा", "or": "ପଚାରନ୍ତୁ",
    },
    "chat_thinking": {
        "en": "…thinking, on this machine…",
        "hi": "…सोच रहा हूँ, इसी मशीन पर…",
        "mr": "…विचार करत आहे, याच मशीनवर…",
        "or": "…ଭାବୁଛି, ଏହି ମେସିନରେ…",
    },
    "chat_noanswer": {
        "en": "(no answer)", "hi": "(कोई उत्तर नहीं)",
        "mr": "(उत्तर नाही)", "or": "(ଉତ୍ତର ନାହିଁ)",
    },
    "chat_ungrounded": {
        "en": "not covered by this video",
        "hi": "इस वीडियो में यह नहीं है",
        "mr": "या व्हिडिओमध्ये हे नाही",
        "or": "ଏହି ଭିଡିଓରେ ଏହା ନାହିଁ",
    },
    "chat_unreachable": {
        "en": "Could not reach the local assistant. Is the app still running?",
        "hi": "स्थानीय सहायक तक पहुँच नहीं हो सकी। क्या ऐप अब भी चल रहा है?",
        "mr": "स्थानिक सहाय्यकाशी संपर्क होऊ शकला नाही. अ‍ॅप अजून सुरू आहे का?",
        "or": "ସ୍ଥାନୀୟ ସହାୟକ ସହ ଯୋଗାଯୋଗ ହୋଇପାରିଲା ନାହିଁ। ଆପ୍ ଏବେ ବି ଚାଲୁଛି କି?",
    },

    # ---------------- voice ----------------
    "voice_blocked": {
        "en": "Microphone blocked — allow microphone access to talk.",
        "hi": "माइक बंद है — बोलने के लिए माइक की अनुमति दें।",
        "mr": "माइक बंद आहे — बोलण्यासाठी माइकला परवानगी द्या.",
        "or": "ମାଇକ ବନ୍ଦ ଅଛି — କହିବା ପାଇଁ ମାଇକକୁ ଅନୁମତି ଦିଅନ୍ତୁ।",
    },
    "voice_listening": {
        "en": "Listening… tap the microphone again to stop.",
        "hi": "सुन रहा हूँ… रोकने के लिए माइक दोबारा दबाएँ।",
        "mr": "ऐकत आहे… थांबवण्यासाठी माइक पुन्हा दाबा.",
        "or": "ଶୁଣୁଛି… ବନ୍ଦ କରିବାକୁ ମାଇକ ପୁଣି ଦବାନ୍ତୁ।",
    },
    "voice_thinking": {
        "en": "Thinking… transcribing and answering, offline.",
        "hi": "सोच रहा हूँ… सुनकर लिख रहा हूँ और उत्तर बना रहा हूँ, बिना इंटरनेट।",
        "mr": "विचार करत आहे… ऐकून लिहीत आहे आणि उत्तर तयार करत आहे, इंटरनेटशिवाय.",
        "or": "ଭାବୁଛି… ଶୁଣି ଲେଖୁଛି ଓ ଉତ୍ତର ପ୍ରସ୍ତୁତ କରୁଛି, ଇଣ୍ଟରନେଟ ବିନା।",
    },
    "voice_speaking": {
        "en": "Speaking…", "hi": "बोल रहा हूँ…",
        "mr": "बोलत आहे…", "or": "କହୁଛି…",
    },
    "voice_error": {
        "en": "Voice error", "hi": "आवाज़ में त्रुटि",
        "mr": "आवाजात त्रुटी", "or": "ସ୍ୱରରେ ତ୍ରୁଟି",
    },
    "voice_nohear": {
        "en": "I could not hear that clearly. Please try again.",
        "hi": "आवाज़ स्पष्ट नहीं सुनाई दी। कृपया दोबारा बोलें।",
        "mr": "आवाज स्पष्ट ऐकू आला नाही. कृपया पुन्हा बोला.",
        "or": "ସ୍ୱର ସ୍ପଷ୍ଟ ଶୁଣାଗଲା ନାହିଁ। ଦୟାକରି ପୁଣି କୁହନ୍ତୁ।",
    },
    "voice_no_asr": {
        "en": "Speech recognition is not available for Odia, so the microphone cannot be used in Odia. Type your question instead — the answer will still be in Odia.",
        "hi": "ओड़िया के लिए वाक् पहचान उपलब्ध नहीं है, इसलिए माइक ओड़िया में काम नहीं करेगा। प्रश्न लिखकर पूछें — उत्तर फिर भी ओड़िया में मिलेगा।",
        "mr": "ओडियासाठी वाचा-ओळख उपलब्ध नाही, त्यामुळे माइक ओडियात चालणार नाही. प्रश्न टाइप करा — उत्तर तरीही ओडियातच मिळेल.",
        "or": "ଓଡ଼ିଆ ପାଇଁ ସ୍ୱର-ଚିହ୍ନଟ ଉପଲବ୍ଧ ନାହିଁ, ତେଣୁ ମାଇକ ଓଡ଼ିଆରେ କାମ କରିବ ନାହିଁ। ପ୍ରଶ୍ନ ଟାଇପ କରନ୍ତୁ — ଉତ୍ତର ତଥାପି ଓଡ଼ିଆରେ ମିଳିବ।",
    },

    # ---------------- settings ----------------
    "set_tag": {
        "en": "operator settings — the farmer flow stays zero-config",
        "hi": "संचालक सेटिंग्स — किसान के लिए कुछ भी सेट करने की ज़रूरत नहीं",
        "mr": "संचालक सेटिंग्ज — शेतकऱ्यासाठी काहीही सेट करण्याची गरज नाही",
        "or": "ପରିଚାଳକ ସେଟିଂସ — କୃଷକଙ୍କ ପାଇଁ କିଛି ସେଟ କରିବାର ଆବଶ୍ୟକତା ନାହିଁ",
    },
    "set_back": {
        "en": "back to videos", "hi": "वीडियो पर वापस",
        "mr": "व्हिडिओंकडे परत", "or": "ଭିଡିଓକୁ ଫେରନ୍ତୁ",
    },
    "set_interface": {
        "en": "Interface language", "hi": "ऐप की भाषा",
        "mr": "अ‍ॅपची भाषा", "or": "ଆପର ଭାଷା",
    },
    "set_interface_lbl": {
        "en": "Language of this app", "hi": "इस ऐप की भाषा",
        "mr": "या अ‍ॅपची भाषा", "or": "ଏହି ଆପର ଭାଷା",
    },
    "set_interface_sub": {
        "en": "buttons, labels and messages — applies immediately",
        "hi": "बटन, लेबल और संदेश — तुरंत लागू",
        "mr": "बटणे, लेबले आणि संदेश — लगेच लागू",
        "or": "ବଟନ, ଲେବଲ ଓ ସନ୍ଦେଶ — ସଙ୍ଗେ ସଙ୍ଗେ ଲାଗୁ",
    },
    "set_popup_lbl": {
        "en": "Ask for the language on the home page",
        "hi": "होम पेज पर भाषा पूछें",
        "mr": "होम पेजवर भाषा विचारा",
        "or": "ହୋମ ପେଜରେ ଭାଷା ପଚାରନ୍ତୁ",
    },
    "set_popup_sub": {
        "en": "show the chooser every time the home page opens — for a shared laptop",
        "hi": "हर बार होम पेज खुलने पर चुनाव दिखाएँ — साझा लैपटॉप के लिए",
        "mr": "प्रत्येक वेळी होम पेज उघडल्यावर निवड दाखवा — सामायिक लॅपटॉपसाठी",
        "or": "ପ୍ରତ୍ୟେକ ଥର ହୋମ ପେଜ ଖୋଲିଲେ ବାଛିବା ଦେଖାନ୍ତୁ — ସହଭାଗୀ ଲାପଟପ ପାଇଁ",
    },
    "set_models": {
        "en": "Models", "hi": "मॉडल", "mr": "मॉडेल्स", "or": "ମଡେଲ",
    },
    "set_asr": {
        "en": "Video transcription", "hi": "वीडियो ट्रांसक्रिप्शन",
        "mr": "व्हिडिओ ट्रान्सक्रिप्शन", "or": "ଭିଡିଓ ଟ୍ରାନ୍ସକ୍ରିପସନ",
    },
    "set_asr_sub": {
        "en": "bigger is more accurate and slower",
        "hi": "बड़ा मॉडल = अधिक सटीक, पर धीमा",
        "mr": "मोठे मॉडेल = अधिक अचूक, पण हळू",
        "or": "ବଡ଼ ମଡେଲ = ଅଧିକ ସଠିକ, କିନ୍ତୁ ଧୀର",
    },
    "set_mic": {
        "en": "Voice input", "hi": "आवाज़ से इनपुट",
        "mr": "आवाजाने इनपुट", "or": "ସ୍ୱର ଇନପୁଟ",
    },
    "set_mic_sub": {
        "en": "microphone clips are short, so a lighter model keeps the reply quick",
        "hi": "माइक की रिकॉर्डिंग छोटी होती है, इसलिए हल्का मॉडल उत्तर जल्दी देता है",
        "mr": "माइकचे रेकॉर्डिंग लहान असते, त्यामुळे हलके मॉडेल उत्तर लवकर देते",
        "or": "ମାଇକ ରେକର୍ଡିଂ ଛୋଟ ହୋଇଥାଏ, ତେଣୁ ହାଲୁକା ମଡେଲ ଉତ୍ତର ଶୀଘ୍ର ଦିଏ",
    },
    "set_mt": {
        "en": "Translation engine", "hi": "अनुवाद इंजन",
        "mr": "भाषांतर इंजिन", "or": "ଅନୁବାଦ ଇଞ୍ଜିନ",
    },
    "set_mt_sub": {
        "en": "IndicTrans2 is measurably better for Hindi, Marathi and Odia; NLLB is the fallback",
        "hi": "हिंदी, मराठी और ओड़िया के लिए IndicTrans2 स्पष्ट रूप से बेहतर है; NLLB विकल्प है",
        "mr": "हिंदी, मराठी आणि ओडियासाठी IndicTrans2 स्पष्टपणे चांगले आहे; NLLB हा पर्याय आहे",
        "or": "ହିନ୍ଦୀ, ମରାଠୀ ଓ ଓଡ଼ିଆ ପାଇଁ IndicTrans2 ସ୍ପଷ୍ଟ ଭାବେ ଭଲ; NLLB ହେଉଛି ବିକଳ୍ପ",
    },
    "set_llm": {
        "en": "Chat model", "hi": "चैट मॉडल", "mr": "चॅट मॉडेल", "or": "ଚାଟ୍ ମଡେଲ",
    },
    "set_llm_sub": {
        "en": "answers questions about the video",
        "hi": "वीडियो के बारे में प्रश्नों का उत्तर देता है",
        "mr": "व्हिडिओबद्दलच्या प्रश्नांची उत्तरे देते",
        "or": "ଭିଡିଓ ବିଷୟରେ ପ୍ରଶ୍ନର ଉତ୍ତର ଦିଏ",
    },
    "set_llm_fb": {
        "en": "Chat model fallback", "hi": "वैकल्पिक चैट मॉडल",
        "mr": "पर्यायी चॅट मॉडेल", "or": "ବିକଳ୍ପ ଚାଟ୍ ମଡେଲ",
    },
    "set_llm_fb_sub": {
        "en": "used when the main one will not fit in memory",
        "hi": "जब मुख्य मॉडल मेमोरी में न आए तब उपयोग होता है",
        "mr": "मुख्य मॉडेल मेमरीत बसत नसेल तेव्हा वापरले जाते",
        "or": "ମୁଖ୍ୟ ମଡେଲ ମେମୋରୀରେ ନ ଧରିଲେ ବ୍ୟବହାର ହୁଏ",
    },
    "set_guide": {
        "en": "Which model for which language?",
        "hi": "किस भाषा के लिए कौन-सा मॉडल?",
        "mr": "कोणत्या भाषेसाठी कोणते मॉडेल?",
        "or": "କେଉଁ ଭାଷା ପାଇଁ କେଉଁ ମଡେଲ?",
    },
    "set_guide_sub": {
        "en": "Scored out of 5 per language. Rows marked measured were benchmarked on BAIF field video on this hardware.",
        "hi": "हर भाषा के लिए 5 में से अंक। “measured” वाली पंक्तियाँ इसी हार्डवेयर पर BAIF के वीडियो से मापी गई हैं।",
        "mr": "प्रत्येक भाषेसाठी 5 पैकी गुण. “measured” अशा ओळी याच हार्डवेअरवर BAIF च्या व्हिडिओवरून मोजल्या आहेत.",
        "or": "ପ୍ରତ୍ୟେକ ଭାଷା ପାଇଁ 5 ମଧ୍ୟରୁ ନମ୍ବର। “measured” ଧାଡ଼ିଗୁଡ଼ିକ ଏହି ହାର୍ଡୱେରରେ BAIF ଭିଡିଓରୁ ମପାଯାଇଛି।",
    },
    "set_langs": {
        "en": "Languages", "hi": "भाषाएँ", "mr": "भाषा", "or": "ଭାଷାସମୂହ",
    },
    "set_langs_lbl": {
        "en": "Target languages to generate",
        "hi": "कौन-सी भाषाएँ बनानी हैं",
        "mr": "कोणत्या भाषा तयार करायच्या",
        "or": "କେଉଁ ଭାଷା ତିଆରି କରିବାକୁ",
    },
    "set_langs_sub": {
        "en": "subtitles, voiceover and answers",
        "hi": "सबटाइटल, आवाज़ और उत्तर",
        "mr": "सबटायटल, आवाज आणि उत्तरे",
        "or": "ସବଟାଇଟଲ, ସ୍ୱର ଓ ଉତ୍ତର",
    },
    "set_perf": {
        "en": "Performance", "hi": "प्रदर्शन", "mr": "कार्यक्षमता", "or": "କାର୍ଯ୍ୟଦକ୍ଷତା",
    },
    "set_threads": {
        "en": "CPU threads", "hi": "CPU थ्रेड", "mr": "CPU थ्रेड्स", "or": "CPU ଥ୍ରେଡ",
    },
    "set_device": {
        "en": "Device", "hi": "डिवाइस", "mr": "डिव्हाइस", "or": "ଡିଭାଇସ",
    },
    "set_device_sub": {
        "en": "use the GPU only when it has enough memory",
        "hi": "GPU तभी चुनें जब उसमें पर्याप्त मेमोरी हो",
        "mr": "GPU तेव्हाच निवडा जेव्हा पुरेशी मेमरी असेल",
        "or": "GPU ସେତେବେଳେ ବାଛନ୍ତୁ ଯେତେବେଳେ ଯଥେଷ୍ଟ ମେମୋରୀ ଥାଏ",
    },
    "set_beam": {
        "en": "Beam size", "hi": "बीम साइज़", "mr": "बीम साइज", "or": "ବିମ ସାଇଜ",
    },
    "set_beam_sub": {
        "en": "1 is fast and stable · higher is more accurate",
        "hi": "1 = तेज़ और स्थिर · अधिक = ज़्यादा सटीक",
        "mr": "1 = जलद आणि स्थिर · जास्त = अधिक अचूक",
        "or": "1 = ଶୀଘ୍ର ଓ ସ୍ଥିର · ଅଧିକ = ଅଧିକ ସଠିକ",
    },
    "set_memsaver": {
        "en": "Memory saver for voice", "hi": "आवाज़ के लिए मेमोरी बचत",
        "mr": "आवाजासाठी मेमरी बचत", "or": "ସ୍ୱର ପାଇଁ ମେମୋରୀ ସଞ୍ଚୟ",
    },
    "set_memsaver_sub": {
        "en": "unload the chat model before transcribing the microphone, on tight memory",
        "hi": "कम मेमोरी पर माइक सुनने से पहले चैट मॉडल हटा दें",
        "mr": "कमी मेमरीवर माइक ऐकण्याआधी चॅट मॉडेल काढून टाका",
        "or": "କମ ମେମୋରୀରେ ମାଇକ ଶୁଣିବା ପୂର୍ବରୁ ଚାଟ୍ ମଡେଲ ହଟାଇଦିଅନ୍ତୁ",
    },
    "set_behaviour": {
        "en": "Chat and voice behaviour", "hi": "चैट और आवाज़ का व्यवहार",
        "mr": "चॅट आणि आवाजाचे वर्तन", "or": "ଚାଟ୍ ଓ ସ୍ୱରର ଆଚରଣ",
    },
    "set_ctx": {
        "en": "Context mode", "hi": "संदर्भ मोड", "mr": "संदर्भ मोड", "or": "ପ୍ରସଙ୍ଗ ମୋଡ",
    },
    "set_ctx_sub": {
        "en": "foreground sends the key lines plus the full transcript — best for small models",
        "hi": "foreground = मुख्य पंक्तियाँ + पूरा ट्रांसक्रिप्ट — छोटे मॉडल के लिए सबसे अच्छा",
        "mr": "foreground = मुख्य ओळी + संपूर्ण ट्रान्सक्रिप्ट — लहान मॉडेलसाठी सर्वोत्तम",
        "or": "foreground = ମୁଖ୍ୟ ଧାଡ଼ି + ସମ୍ପୂର୍ଣ୍ଣ ଟ୍ରାନ୍ସକ୍ରିପ୍ଟ — ଛୋଟ ମଡେଲ ପାଇଁ ସର୍ବୋତ୍ତମ",
    },
    "set_temp": {
        "en": "Answer creativity", "hi": "उत्तर की रचनात्मकता",
        "mr": "उत्तराची सर्जनशीलता", "or": "ଉତ୍ତରର ସୃଜନଶୀଳତା",
    },
    "set_temp_sub": {
        "en": "lower is more factual", "hi": "कम = अधिक तथ्यपरक",
        "mr": "कमी = अधिक तथ्यावर आधारित", "or": "କମ = ଅଧିକ ତଥ୍ୟଭିତ୍ତିକ",
    },
    "set_autospeak": {
        "en": "Speak answers automatically", "hi": "उत्तर अपने आप बोलें",
        "mr": "उत्तरे आपोआप बोला", "or": "ଉତ୍ତର ନିଜେ ନିଜେ କୁହନ୍ତୁ",
    },
    "set_autospeak_sub": {
        "en": "play the spoken reply as soon as it is ready",
        "hi": "उत्तर तैयार होते ही बोलकर सुनाएँ",
        "mr": "उत्तर तयार होताच बोलून ऐकवा",
        "or": "ଉତ୍ତର ପ୍ରସ୍ତୁତ ହେବା ମାତ୍ରେ କହି ଶୁଣାନ୍ତୁ",
    },
    "set_save": {
        "en": "Save settings", "hi": "सेटिंग्स सहेजें",
        "mr": "सेटिंग्ज जतन करा", "or": "ସେଟିଂସ ସେଭ କରନ୍ତୁ",
    },
    "set_saved": {
        "en": "Saved", "hi": "सहेजा गया", "mr": "जतन झाले", "or": "ସେଭ ହେଲା",
    },
    "set_save_note": {
        "en": "Model changes apply to new processing. Use Re-process on a video to apply them to it.",
        "hi": "मॉडल के बदलाव नई प्रोसेसिंग पर लागू होते हैं। किसी वीडियो पर लागू करने के लिए “दोबारा प्रक्रिया” चुनें।",
        "mr": "मॉडेलचे बदल नव्या प्रोसेसिंगला लागू होतात. एखाद्या व्हिडिओला लागू करण्यासाठी “पुन्हा प्रक्रिया” वापरा.",
        "or": "ମଡେଲର ପରିବର୍ତ୍ତନ ନୂଆ ପ୍ରକ୍ରିୟାରେ ଲାଗୁ ହୁଏ। କୌଣସି ଭିଡିଓରେ ଲାଗୁ କରିବାକୁ “ପୁନଃ ପ୍ରକ୍ରିୟା” ବ୍ୟବହାର କରନ୍ତୁ।",
    },
    "set_status": {
        "en": "System status", "hi": "सिस्टम स्थिति",
        "mr": "सिस्टम स्थिती", "or": "ସିଷ୍ଟମ ସ୍ଥିତି",
    },
    "st_runtime": {
        "en": "Runtime", "hi": "रनटाइम", "mr": "रनटाइम", "or": "ରନଟାଇମ",
    },
    "st_ram": {
        "en": "Free memory", "hi": "खाली मेमोरी",
        "mr": "मोकळी मेमरी", "or": "ଖାଲି ମେମୋରୀ",
    },
    "st_chatmodels": {
        "en": "Chat models", "hi": "चैट मॉडल", "mr": "चॅट मॉडेल्स", "or": "ଚାଟ୍ ମଡେଲ",
    },
    "st_whisper": {
        "en": "Transcription sizes", "hi": "ट्रांसक्रिप्शन आकार",
        "mr": "ट्रान्सक्रिप्शन आकार", "or": "ଟ୍ରାନ୍ସକ୍ରିପସନ ଆକାର",
    },
    "st_tts": {
        "en": "Voices", "hi": "आवाज़ें", "mr": "आवाज", "or": "ସ୍ୱରସମୂହ",
    },
    "set_status_note": {
        "en": "This page never downloads anything. It only switches between what is already installed.",
        "hi": "यह पेज कभी कुछ डाउनलोड नहीं करता। यह केवल पहले से मौजूद विकल्पों के बीच बदलाव करता है।",
        "mr": "हे पेज कधीही काहीही डाउनलोड करत नाही. ते फक्त आधीपासून असलेल्या पर्यायांमध्ये बदल करते.",
        "or": "ଏହି ପେଜ କେବେ ବି କିଛି ଡାଉନଲୋଡ କରେ ନାହିଁ। ଏହା କେବଳ ପୂର୍ବରୁ ଥିବା ବିକଳ୍ପ ମଧ୍ୟରେ ବଦଳାଏ।",
    },
    "yes": {"en": "yes", "hi": "हाँ", "mr": "होय", "or": "ହଁ"},
    "no": {"en": "no", "hi": "नहीं", "mr": "नाही", "or": "ନାହିଁ"},

    # ---------------- model garden ----------------
    "gd_tag": {
        "en": "every model scored for this machine",
        "hi": "हर मॉडल, इसी मशीन के हिसाब से आँका गया",
        "mr": "प्रत्येक मॉडेल, याच मशीनसाठी मोजलेले",
        "or": "ପ୍ରତ୍ୟେକ ମଡେଲ, ଏହି ମେସିନ ପାଇଁ ମପାଯାଇଛି",
    },
    "gd_machine": {
        "en": "This machine", "hi": "यह मशीन", "mr": "ही मशीन", "or": "ଏହି ମେସିନ",
    },
    "gd_bestfor": {
        "en": "What to use — for this machine",
        "hi": "क्या उपयोग करें — इस मशीन के लिए",
        "mr": "काय वापरावे — या मशीनसाठी",
        "or": "କଣ ବ୍ୟବହାର କରିବେ — ଏହି ମେସିନ ପାଇଁ",
    },
    "gd_quality": {
        "en": "Quality by language", "hi": "भाषा के अनुसार गुणवत्ता",
        "mr": "भाषेनुसार गुणवत्ता", "or": "ଭାଷା ଅନୁସାରେ ଗୁଣବତ୍ତା",
    },
    "gd_presets": {
        "en": "One-click presets", "hi": "एक क्लिक में सेट",
        "mr": "एका क्लिकमध्ये सेट", "or": "ଏକ କ୍ଲିକରେ ସେଟ",
    },
    "gd_apply": {
        "en": "Apply", "hi": "लागू करें", "mr": "लागू करा", "or": "ଲାଗୁ କରନ୍ତୁ",
    },
    "gd_nodl": {
        "en": "Nothing here downloads anything.",
        "hi": "यहाँ कुछ भी डाउनलोड नहीं होता।",
        "mr": "इथे काहीही डाउनलोड होत नाही.",
        "or": "ଏଠାରେ କିଛି ଡାଉନଲୋଡ ହୁଏ ନାହିଁ।",
    },
    "gd_lede": {
        "en": "Every model this build can use, scored per language and measured against the machine it is running on. Scores are 1 to 5. A dash means the model cannot do that language at all, which is different from doing it badly.",
        "hi": "इस बिल्ड में उपलब्ध हर मॉडल, हर भाषा के लिए और इसी मशीन पर आँका गया। अंक 1 से 5 तक। डैश का अर्थ है कि मॉडल उस भाषा को कर ही नहीं सकता — यह खराब करने से अलग बात है।",
        "mr": "या बिल्डमधील प्रत्येक मॉडेल, प्रत्येक भाषेसाठी आणि याच मशीनवर मोजलेले. गुण 1 ते 5. डॅशचा अर्थ मॉडेल ती भाषा करूच शकत नाही — हे वाईट करण्यापेक्षा वेगळे आहे.",
        "or": "ଏହି ବିଲ୍ଡରେ ଥିବା ପ୍ରତ୍ୟେକ ମଡେଲ, ପ୍ରତ୍ୟେକ ଭାଷା ପାଇଁ ଏବଂ ଏହି ମେସିନରେ ମପାଯାଇଛି। ନମ୍ବର 1 ରୁ 5। ଡ୍ୟାସର ଅର୍ଥ ମଡେଲ ସେହି ଭାଷା କରିପାରେ ନାହିଁ — ଏହା ଖରାପ କରିବାଠାରୁ ଭିନ୍ନ।",
    },
    "gd_tier": {"en": "Tier", "hi": "श्रेणी", "mr": "श्रेणी", "or": "ଶ୍ରେଣୀ"},
    "gd_memory": {"en": "Memory", "hi": "मेमोरी", "mr": "मेमरी", "or": "ମେମୋରୀ"},
    "gd_cpu": {"en": "CPU", "hi": "CPU", "mr": "CPU", "or": "CPU"},
    "gd_gpu": {"en": "GPU", "hi": "GPU", "mr": "GPU", "or": "GPU"},
    "gd_disk": {"en": "Free disk", "hi": "खाली डिस्क", "mr": "मोकळी डिस्क", "or": "ଖାଲି ଡିସ୍କ"},
    "gd_none": {"en": "None", "hi": "कोई नहीं", "mr": "काहीही नाही", "or": "କିଛି ନାହିଁ"},
    "gd_cpu_note": {
        "en": "everything runs on CPU by default",
        "hi": "डिफ़ॉल्ट रूप से सब कुछ CPU पर चलता है",
        "mr": "डीफॉल्टनुसार सर्व काही CPU वर चालते",
        "or": "ଡିଫଲ୍ଟ ଭାବେ ସବୁ CPU ରେ ଚାଲେ",
    },
    "gd_gpu_none": {
        "en": "CPU-only — the supported baseline",
        "hi": "केवल CPU — यही समर्थित आधार है",
        "mr": "फक्त CPU — हाच आधारभूत पर्याय आहे",
        "or": "କେବଳ CPU — ଏହା ହିଁ ସମର୍ଥିତ ଆଧାର",
    },
    "gd_free_now": {"en": "free now", "hi": "अभी खाली", "mr": "आता मोकळी", "or": "ବର୍ତ୍ତମାନ ଖାଲି"},
    "gd_installed_disk": {
        "en": "of models installed", "hi": "मॉडल इंस्टॉल हैं",
        "mr": "मॉडेल्स इन्स्टॉल आहेत", "or": "ମଡେଲ ଇନଷ୍ଟଲ ଅଛି",
    },
    "gd_task": {"en": "Task", "hi": "कार्य", "mr": "काम", "or": "କାର୍ଯ୍ୟ"},
    "gd_model": {"en": "Model", "hi": "मॉडल", "mr": "मॉडेल", "or": "ମଡେଲ"},
    "gd_speed": {"en": "Speed", "hi": "गति", "mr": "वेग", "or": "ଗତି"},
    "gd_ram": {"en": "RAM", "hi": "RAM", "mr": "RAM", "or": "RAM"},
    "gd_load": {"en": "Load", "hi": "लोड", "mr": "लोड", "or": "ଲୋଡ"},
    "gd_licence": {"en": "Licence", "hi": "लाइसेंस", "mr": "परवाना", "or": "ଲାଇସେନ୍ସ"},
    "gd_status": {"en": "Status", "hi": "स्थिति", "mr": "स्थिती", "or": "ସ୍ଥିତି"},
    "gd_why": {"en": "Why / when", "hi": "क्यों / कब", "mr": "का / कधी", "or": "କାହିଁକି / କେବେ"},
    "gd_installed": {"en": "installed", "hi": "इंस्टॉल है", "mr": "इन्स्टॉल आहे", "or": "ଇନଷ୍ଟଲ ଅଛି"},
    "gd_notinstalled": {
        "en": "not installed", "hi": "इंस्टॉल नहीं",
        "mr": "इन्स्टॉल नाही", "or": "ଇନଷ୍ଟଲ ନାହିଁ",
    },
    "gd_tight": {"en": "tight", "hi": "मुश्किल", "mr": "अडचणीचे", "or": "ଅସୁବିଧା"},
    "gd_transcribe": {
        "en": "Transcribe", "hi": "ट्रांसक्राइब",
        "mr": "ट्रान्सक्राइब", "or": "ଟ୍ରାନ୍ସକ୍ରାଇବ",
    },
    "gd_translate": {"en": "Translate", "hi": "अनुवाद", "mr": "भाषांतर", "or": "ଅନୁବାଦ"},
    "gd_chat": {"en": "Chat", "hi": "चैट", "mr": "चॅट", "or": "ଚାଟ୍"},
    "gd_recommended": {
        "en": "RECOMMENDED", "hi": "अनुशंसित", "mr": "शिफारस केलेले", "or": "ସୁପାରିଶ",
    },
    "gd_legend": {
        "en": "5 excellent · 4 good · 3 usable · 2 poor · 1 unusable · — not supported by this model",
        "hi": "5 उत्कृष्ट · 4 अच्छा · 3 काम लायक · 2 कमज़ोर · 1 अनुपयोगी · — यह मॉडल इसे नहीं करता",
        "mr": "5 उत्कृष्ट · 4 चांगले · 3 वापरण्यायोग्य · 2 कमकुवत · 1 निरुपयोगी · — हे मॉडेल हे करत नाही",
        "or": "5 ଉତ୍କୃଷ୍ଟ · 4 ଭଲ · 3 ବ୍ୟବହାରଯୋଗ୍ୟ · 2 ଦୁର୍ବଳ · 1 ଅନୁପଯୋଗୀ · — ଏହି ମଡେଲ ଏହା କରେ ନାହିଁ",
    },
    "gd_odia_title": {
        "en": "Why Odia has no transcription score.",
        "hi": "ओड़िया का ट्रांसक्रिप्शन अंक क्यों नहीं है।",
        "mr": "ओडियाला ट्रान्सक्रिप्शन गुण का नाही.",
        "or": "ଓଡ଼ିଆର ଟ୍ରାନ୍ସକ୍ରିପସନ ନମ୍ବର କାହିଁକି ନାହିଁ।",
    },
    "gd_odia_body": {
        "en": "No open speech model can transcribe Odia, so every transcription row is a dash for it. Odia is still a first-class output: Marathi or Hindi speech is transcribed, translated, then spoken by the Odia voice — which is the common BAIF case, a Marathi field video for an Odia audience.",
        "hi": "कोई भी खुला वाक् मॉडल ओड़िया को ट्रांसक्राइब नहीं कर सकता, इसलिए हर ट्रांसक्रिप्शन पंक्ति में डैश है। फिर भी ओड़िया पूरा आउटपुट है: मराठी या हिंदी भाषण ट्रांसक्राइब होता है, अनुवाद होता है, और ओड़िया आवाज़ में बोला जाता है — BAIF का सामान्य मामला यही है।",
        "mr": "कोणतेही खुले वाचा-मॉडेल ओडिया ट्रान्सक्राइब करू शकत नाही, म्हणून प्रत्येक ट्रान्सक्रिप्शन ओळीत डॅश आहे. तरीही ओडिया पूर्ण आउटपुट आहे: मराठी किंवा हिंदी भाषण ट्रान्सक्राइब होते, भाषांतर होते आणि ओडिया आवाजात बोलले जाते — BAIF चे नेहमीचे प्रकरण हेच आहे.",
        "or": "କୌଣସି ମୁକ୍ତ ସ୍ୱର ମଡେଲ ଓଡ଼ିଆ ଟ୍ରାନ୍ସକ୍ରାଇବ କରିପାରେ ନାହିଁ, ତେଣୁ ପ୍ରତ୍ୟେକ ଟ୍ରାନ୍ସକ୍ରିପସନ ଧାଡ଼ିରେ ଡ୍ୟାସ ଅଛି। ତଥାପି ଓଡ଼ିଆ ପୂର୍ଣ୍ଣ ଆଉଟପୁଟ: ମରାଠୀ କିମ୍ବା ହିନ୍ଦୀ ଭାଷଣ ଟ୍ରାନ୍ସକ୍ରାଇବ ହୁଏ, ଅନୁବାଦ ହୁଏ ଓ ଓଡ଼ିଆ ସ୍ୱରରେ କୁହାଯାଏ — BAIF ର ସାଧାରଣ ପରିସ୍ଥିତି ଏହା ହିଁ।",
    },
    "gd_nodl_body": {
        "en": "The Garden reports only what is on this disk. A model shown as not installed is present in the FULL package; it is never fetched at runtime.",
        "hi": "गार्डन केवल इसी डिस्क पर मौजूद चीज़ें दिखाता है। जो मॉडल “इंस्टॉल नहीं” दिखता है वह FULL पैकेज में है; चलते समय कभी डाउनलोड नहीं होता।",
        "mr": "गार्डन फक्त याच डिस्कवर असलेले दाखवते. “इन्स्टॉल नाही” दिसणारे मॉडेल FULL पॅकेजमध्ये आहे; चालू असताना ते कधीही डाउनलोड होत नाही.",
        "or": "ଗାର୍ଡେନ କେବଳ ଏହି ଡିସ୍କରେ ଥିବା ଜିନିଷ ଦେଖାଏ। “ଇନଷ୍ଟଲ ନାହିଁ” ଦେଖାଉଥିବା ମଡେଲ FULL ପ୍ୟାକେଜରେ ଅଛି; ଚାଲିବା ସମୟରେ କେବେ ଡାଉନଲୋଡ ହୁଏ ନାହିଁ।",
    },
}


def normalise(code: str | None) -> str:
    """Accept anything, return a language this app actually has strings for."""
    if not code:
        return DEFAULT_UI
    code = str(code).strip().lower().replace("_", "-")
    if code in UI_LANGS:
        return code
    base = code.split("-")[0]           # en-GB -> en, hi-IN -> hi
    return base if base in UI_LANGS else DEFAULT_UI


def t(key: str, lang: str = DEFAULT_UI) -> str:
    """One string. Falls back to English, then to the key itself."""
    row = S.get(key)
    if not row:
        return key
    return row.get(normalise(lang)) or row.get(DEFAULT_UI) or key


def pack(lang: str = DEFAULT_UI) -> dict[str, str]:
    """Every string in one language, ready for Jinja and for `|tojson`.

    Built per request rather than cached per language: the catalogue is a few
    hundred short strings, so the cost is microseconds, and a shared cached dict
    would be handed to threads that could mutate it.
    """
    lang = normalise(lang)
    return {k: (v.get(lang) or v.get(DEFAULT_UI) or k) for k, v in S.items()}


def choices() -> list[dict[str, str]]:
    """The picker's rows: code, native name, and the English name beneath it."""
    return [{"code": c, "native": UI_NAMES[c], "english": UI_SUBTITLES[c]}
            for c in UI_LANGS]


def missing() -> dict[str, list[str]]:
    """Keys absent from each non-English language. The test suite asserts this is
    empty, so an untranslated string fails a test rather than reaching a reviewer."""
    return {L: sorted(k for k, v in S.items() if not v.get(L))
            for L in UI_LANGS if L != DEFAULT_UI}
