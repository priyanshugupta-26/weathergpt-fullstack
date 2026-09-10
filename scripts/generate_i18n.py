"""
Generate complete, canonical i18n dictionary files for all 22 official languages in the
Eighth Schedule of the Indian Constitution plus English (23 languages total).
"""
import json
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "frontend" / "lib" / "i18n"
DEST.mkdir(parents=True, exist_ok=True)

# 1. Canonical English dictionary
EN = {
    "brand": {
        "name": "WeatherGPT",
        "tagline": "AI Weather & Disaster Intelligence for India",
        "beta": "BETA"
    },
    "nav": {
        "overview": "Overview",
        "globe": "Live globe",
        "forecast": "Forecast",
        "chat": "WeatherGPT",
        "alerts": "Alert center",
        "climate": "Climate analytics",
        "agriculture": "Agriculture",
        "aviation": "Aviation",
        "marine": "Marine",
        "cityMonitor": "Smart city",
        "dataLab": "Data & Learning Lab",
        "modelLab": "Model lab",
        "dashboard": "My dashboard",
        "apiSetup": "API setup",
        "settings": "Settings",
        "systemStatus": "System status",
        "profile": "Profile",
        "logout": "Sign out"
    },
    "auth": {
        "createAccount": "Create your WeatherGPT Account",
        "registerTitle": "AI Weather & Disaster Intelligence for India",
        "registerSubtitle": "Real-time forecast, official IMD alerts, and ML models across 22 Indian languages",
        "fullName": "Full Name",
        "fullNamePlaceholder": "e.g. Priya Sharma",
        "email": "Email Address",
        "emailPlaceholder": "priya@example.com",
        "mobile": "Mobile Number",
        "mobilePlaceholder": "9876543210 (Optional)",
        "password": "Password",
        "passwordHint": "At least 8 characters",
        "confirmPassword": "Confirm Password",
        "state": "State",
        "statePlaceholder": "e.g. Bihar, Maharashtra",
        "district": "District / City",
        "districtPlaceholder": "e.g. Patna, Mumbai",
        "preferredLanguage": "Preferred Language",
        "termsAgree": "I agree to Terms & Privacy Policy",
        "submitRegister": "Create Account",
        "creatingAccount": "Creating account...",
        "alreadyRegistered": "Already registered? Login",
        "loginTitle": "Welcome Back to WeatherGPT",
        "loginSubtitle": "Sign in to access your dashboard, saved locations, and customized alerts",
        "emailOrMobile": "Email or Mobile Number",
        "emailOrMobilePlaceholder": "Email or 10-digit mobile number",
        "submitLogin": "Sign In",
        "loggingIn": "Signing in...",
        "forgotPassword": "Forgot Password?",
        "dontHaveAccount": "Don't have an account? Create one",
        "passwordsDoNotMatch": "Passwords do not match",
        "agreeTermsError": "Please agree to the Terms & Privacy Policy to continue"
    },
    "onboarding": {
        "title": "Welcome to WeatherGPT",
        "subtitle": "Personalize your meteorological intelligence in three quick steps",
        "step1Title": "Step 1: Choose Your Language",
        "step1Desc": "WeatherGPT will provide forecasts, alerts, and AI explanations in your chosen language.",
        "step2Title": "Step 2: Set Primary Location",
        "step2Desc": "Get instant hyperlocal weather and early disaster warnings for your district.",
        "useCurrentLocation": "Use My Current Location",
        "detectingLocation": "Detecting location...",
        "orManual": "Or enter location manually:",
        "step3Title": "Step 3: Alert Preferences",
        "step3Desc": "Select the severe weather conditions you want to be notified about.",
        "heavyRain": "Heavy Rain",
        "thunderstorm": "Thunderstorm",
        "lightning": "Lightning",
        "cyclone": "Cyclone",
        "flood": "Flood",
        "heatwave": "Heatwave",
        "coldWave": "Cold Wave",
        "strongWind": "Strong Wind",
        "earthquake": "Earthquake",
        "marine": "Marine Hazards",
        "enterPortal": "Enter WeatherGPT",
        "skip": "Skip for now",
        "saving": "Saving preferences..."
    },
    "weather": {
        "temperature": "Temperature",
        "feelsLike": "Feels like",
        "humidity": "Humidity",
        "pressure": "Pressure",
        "surfacePressure": "Surface Pressure",
        "rainfall": "Rainfall",
        "precipitation": "Precipitation",
        "precipitationProbability": "Precipitation Probability",
        "wind": "Wind",
        "windSpeed": "Wind Speed",
        "windDirection": "Wind Direction",
        "windGust": "Wind Gust",
        "cloudCover": "Cloud Cover",
        "visibility": "Visibility",
        "uvIndex": "UV Index",
        "airQuality": "Air Quality",
        "dewPoint": "Dew Point",
        "forecast": "Forecast",
        "today": "Today",
        "tomorrow": "Tomorrow",
        "hourly": "Hourly Forecast",
        "daily": "Daily Forecast",
        "currentConditions": "Current Conditions",
        "historical": "Historical Weather"
    },
    "alerts": {
        "warning": "Warning",
        "severe": "Severe Alert",
        "cyclone": "Cyclone",
        "thunderstorm": "Thunderstorm",
        "lightning": "Lightning",
        "flood": "Flood",
        "heatwave": "Heatwave",
        "coldWave": "Cold Wave",
        "earthquake": "Earthquake",
        "activeAlerts": "Active Alerts",
        "noAlerts": "No active weather warnings for this area",
        "imdOriginal": "IMD ORIGINAL",
        "weathergptTranslation": "WEATHERGPT TRANSLATION"
    },
    "common": {
        "search": "Search city, district or coordinates...",
        "loading": "Loading...",
        "save": "Save Changes",
        "saved": "Saved successfully",
        "cancel": "Cancel",
        "error": "Error",
        "language": "Language",
        "theme": "Theme",
        "dark": "Dark",
        "light": "Light",
        "system": "System",
        "source": "Source",
        "engine": "Engine",
        "auto": "Auto",
        "mlModel": "WeatherGPT ML",
        "openMeteo": "Open-Meteo"
    }
}

# 2. Hindi (hi)
HI = {
    "brand": {"name": "WeatherGPT", "tagline": "भारत के लिए एआई मौसम और आपदा सूचना", "beta": "बीटा"},
    "nav": {
        "overview": "अवलोकन", "globe": "लाइव ग्लोब", "forecast": "पूर्वानुमान",
        "chat": "WeatherGPT", "alerts": "चेतावनी केंद्र", "climate": "जलवायु विश्लेषण",
        "agriculture": "कृषि मौसम", "aviation": "विमानन", "marine": "समुद्री मौसम",
        "cityMonitor": "स्मार्ट शहर", "dataLab": "डेटा और लर्निंग लैब", "modelLab": "मॉडल लैब",
        "dashboard": "मेरा डैशबोर्ड", "apiSetup": "एपीआई सेटअप", "settings": "सेटिंग्स",
        "systemStatus": "सिस्टम स्थिति", "profile": "प्रोफ़ाइल", "logout": "साइन आउट"
    },
    "auth": {
        "createAccount": "अपना WeatherGPT खाता बनाएं",
        "registerTitle": "भारत के लिए एआई मौसम और आपदा सूचना",
        "registerSubtitle": "22 भारतीय भाषाओं में वास्तविक समय पूर्वानुमान, आईएमडी अलर्ट और एमएल मॉडल",
        "fullName": "पूरा नाम", "fullNamePlaceholder": "उदा. प्रिया शर्मा",
        "email": "ईमेल पता", "emailPlaceholder": "priya@example.com",
        "mobile": "मोबाइल नंबर", "mobilePlaceholder": "9876543210 (वैकल्पिक)",
        "password": "पासवर्ड", "passwordHint": "कम से कम 8 अक्षर",
        "confirmPassword": "पासवर्ड की पुष्टि करें",
        "state": "राज्य", "statePlaceholder": "उदा. बिहार, महाराष्ट्र",
        "district": "जिला / शहर", "districtPlaceholder": "उदा. पटना, मुंबई",
        "preferredLanguage": "पसंदीदा भाषा",
        "termsAgree": "मैं नियम और गोपनीयता नीति से सहमत हूँ",
        "submitRegister": "खाता बनाएं", "creatingAccount": "खाता बनाया जा रहा है...",
        "alreadyRegistered": "पहले से पंजीकृत हैं? लॉगिन करें",
        "loginTitle": "WeatherGPT में आपका स्वागत है",
        "loginSubtitle": "डैशबोर्ड और अलर्ट एक्सेस करने के लिए साइन इन करें",
        "emailOrMobile": "ईमेल या मोबाइल नंबर", "emailOrMobilePlaceholder": "ईमेल या 10 अंकों का मोबाइल",
        "submitLogin": "साइन इन करें", "loggingIn": "साइन इन हो रहा है...",
        "forgotPassword": "पासवर्ड भूल गए?", "dontHaveAccount": "खाता नहीं है? नया बनाएं",
        "passwordsDoNotMatch": "पासवर्ड मेल नहीं खाते",
        "agreeTermsError": "कृपया आगे बढ़ने के लिए नियमों से सहमत हों"
    },
    "onboarding": {
        "title": "WeatherGPT में आपका स्वागत है",
        "subtitle": "तीन आसान चरणों में अपना मौसम सेटअप पूरा करें",
        "step1Title": "चरण 1: अपनी भाषा चुनें",
        "step1Desc": "WeatherGPT आपकी चुनी हुई भाषा में पूर्वानुमान और चेतावनियाँ प्रदान करेगा।",
        "step2Title": "चरण 2: प्राथमिक स्थान सेट करें",
        "step2Desc": "अपने जिले के लिए सटीक स्थानीय मौसम और त्वरित आपदा चेतावनी पाएं।",
        "useCurrentLocation": "मेरे वर्तमान स्थान का उपयोग करें",
        "detectingLocation": "स्थान खोजा जा रहा है...",
        "orManual": "या स्थान मैन्युअल दर्ज करें:",
        "step3Title": "चरण 3: अलर्ट प्राथमिकताएं",
        "step3Desc": "गंभीर मौसम चुनें जिसके लिए आप सूचनाएं प्राप्त करना चाहते हैं।",
        "heavyRain": "भारी बारिश", "thunderstorm": "आंधी-तूफान", "lightning": "बिजली गिरना",
        "cyclone": "चक्रवात", "flood": "बाढ़", "heatwave": "लू / ताप लहर",
        "coldWave": "शीत लहर", "strongWind": "तेज हवाएं", "earthquake": "भूकंप",
        "marine": "समुद्री खतरे", "enterPortal": "WeatherGPT खोलें",
        "skip": "अभी छोड़ें", "saving": "प्राथमिकताएं सहेजी जा रही हैं..."
    },
    "weather": {
        "temperature": "तापमान", "feelsLike": "महसूस", "humidity": "आर्द्रता",
        "pressure": "वायुदाब", "surfacePressure": "सतह दबाव", "rainfall": "वर्षा",
        "precipitation": "वर्षा की मात्रा", "precipitationProbability": "वर्षा की संभावना",
        "wind": "हवा", "windSpeed": "हवा की गति", "windDirection": "हवा की दिशा",
        "windGust": "हवा के झोंके", "cloudCover": "बादल", "visibility": "दृश्यता",
        "uvIndex": "यूवी इंडेक्स", "airQuality": "वायु गुणवत्ता (AQI)", "dewPoint": "ओस बिंदु",
        "forecast": "पूर्वानुमान", "today": "आज", "tomorrow": "कल",
        "hourly": "प्रति घंटा पूर्वानुमान", "daily": "दैनिक पूर्वानुमान",
        "currentConditions": "वर्तमान स्थिति", "historical": "ऐतिहासिक मौसम"
    },
    "alerts": {
        "warning": "चेतावनी", "severe": "गंभीर अलर्ट", "cyclone": "चक्रवात",
        "thunderstorm": "आंधी-तूफान", "lightning": "बिजली चमकना", "flood": "बाढ़",
        "heatwave": "लू", "coldWave": "शीत लहर", "earthquake": "भूकंप",
        "activeAlerts": "सक्रिय चेतावनियां", "noAlerts": "इस क्षेत्र के लिए कोई सक्रिय चेतावनी नहीं है",
        "imdOriginal": "आईएमडी मूल चेतावनी", "weathergptTranslation": "WeatherGPT अनुवाद"
    },
    "common": {
        "search": "शहर, जिला या निर्देशांक खोजें...", "loading": "लोड हो रहा है...",
        "save": "सहेजें", "saved": "सफलतापूर्वक सहेजा गया", "cancel": "रद्द करें",
        "error": "त्रुटि", "language": "भाषा", "theme": "थीम",
        "dark": "डार्क", "light": "लाइट", "system": "सिस्टम",
        "source": "स्रोत", "engine": "इंजन", "auto": "ऑटो",
        "mlModel": "WeatherGPT एमएल", "openMeteo": "ओपन-मेटियो"
    }
}

# Translations template generator for other Indian languages
# We define curated lexicons for all 21 remaining Eighth Schedule languages
INDIAN_LANGUAGES = {
    "as": {  # Assamese
        "tagline": "ভাৰতৰ বাবে এআই বতৰ আৰু দুৰ্যোগ তথ্য",
        "overview": "অৱলোকন", "globe": "লাইভ গ্ল’ব", "forecast": "বতৰৰ পূৰ্বাভাস",
        "alerts": "সতৰ্কতা কেন্দ্ৰ", "climate": "জলবায়ু বিশ্লেষণ", "agriculture": "কৃষি বতৰ",
        "aviation": "বিমান পৰিবহণ", "marine": "সামুদ্ৰিক বতৰ", "cityMonitor": "স্মাৰ্ট চহৰ",
        "dataLab": "ডাটা আৰু লাৰ্নিং লেব", "modelLab": "মডেল লেব", "dashboard": "মোৰ ডেচব’ৰ্ড",
        "settings": "ছেটিংছ", "logout": "লগ আউট", "createAccount": "WeatherGPT একাউণ্ট সৃষ্টি কৰক",
        "fullName": "সম্পূৰ্ণ নাম", "email": "ইমেইল ঠিকনা", "mobile": "ম’বাইল নম্বৰ",
        "password": "পাছৱৰ্ড", "confirmPassword": "পাছৱৰ্ড নিশ্চিত কৰক", "state": "ৰাজ্য",
        "district": "জিলা / চহৰ", "preferredLanguage": "পছন্দৰ ভাষা",
        "submitRegister": "একাউণ্ট খোলক", "loginTitle": "লগইন কৰক",
        "temperature": "উষ্ণতা", "humidity": "আৰ্দ্ৰতা", "pressure": "বায়ু চাপ",
        "rainfall": "বৰষুণ", "wind": "বতাহ", "windSpeed": "বতাহৰ গতি",
        "cyclone": "ঘূৰ্ণিবতাহ", "thunderstorm": "বজ্ৰপাত", "flood": "বানপানী",
        "heatwave": "তাপপ্ৰৱাহ", "earthquake": "ভূমিকম্প", "warning": "সতৰ্কবাণী"
    },
    "bn": {  # Bengali
        "tagline": "ভারতের জন্য এআই আবহাওয়া ও দুর্যোগ গোয়েন্দা তথ্য",
        "overview": "সংক্ষিপ্ত বিবরণ", "globe": "লাইভ গ্লোব", "forecast": "আবহাওয়ার পূর্বাভাস",
        "alerts": "সতর্কতা কেন্দ্র", "climate": "জলবায়ু বিশ্লেষণ", "agriculture": "কৃষি আবহাওয়া",
        "aviation": "বিমান চলাচল", "marine": "সামুদ্রিক আবহাওয়া", "cityMonitor": "স্মার্ট সিটি",
        "dataLab": "ডাটা ও লার্নিং ল্যাব", "modelLab": "মডেল ল্যাব", "dashboard": "আমার ড্যাশবোর্ড",
        "settings": "সেটিংস", "logout": "সাইন আউট", "createAccount": "WeatherGPT অ্যাকাউন্ট তৈরি করুন",
        "fullName": "পুরো নাম", "email": "ইমেল ঠিকানা", "mobile": "মোবাইল নম্বর",
        "password": "পাসওয়ার্ড", "confirmPassword": "পাসওয়ার্ড নিশ্চিত করুন", "state": "রাজ্য",
        "district": "জেলা / শহর", "preferredLanguage": "পছন্দের ভাষা",
        "submitRegister": "অ্যাকাউন্ট খুলুন", "loginTitle": "লগইন করুন",
        "temperature": "তাপমাত্রা", "humidity": "আর্দ্রতা", "pressure": "বায়ুচাপ",
        "rainfall": "বৃষ্টিপাত", "wind": "বাতাস", "windSpeed": "বাতাসের গতি",
        "cyclone": "ঘূর্ণিঝড়", "thunderstorm": "বজ্রঝড়", "flood": "বন্যা",
        "heatwave": "তাপপ্রবাহ", "earthquake": "ভূমিকম্প", "warning": "সতর্কবার্তা"
    },
    "brx": {  # Bodo
        "tagline": "भारतनि थाखाय एआई बारहावा आरो खैफौ मिथिसारनाय",
        "overview": "नायबिजिरनाय", "globe": "लाइभ ग्लोब", "forecast": "बारहावा सिगां फोरमायनाय",
        "alerts": "हुसियार खालामग्रा मिरु", "climate": "बारहावा बिजिरनाय", "agriculture": "आबाद बारहावा",
        "aviation": "बिरदाव संथान", "marine": "लैथो बारहावा", "cityMonitor": "स्मार्ट सहर",
        "dataLab": "डाटा आरो फोरोंनाय लेब", "modelLab": "मडेल लेब", "dashboard": "आंनि डेशबोर्ड",
        "settings": "सेटिंफोर", "logout": "अंखां", "createAccount": "WeatherGPT एकाउन्ट बानाय",
        "fullName": "गासै मुं", "email": "इमेल", "mobile": "मबाइल नम्बर",
        "password": "पासवर्ड", "confirmPassword": "पासवर्ड थि खालाम", "state": "रायजो",
        "district": "जिल्ला / सहर", "preferredLanguage": "मोजां मोननाय राव",
        "submitRegister": "एकाउन्ट बानाय", "loginTitle": "हाब",
        "temperature": "दुंथाइ", "humidity": "सिदोबथि", "pressure": "बारनि नारसिननाय",
        "rainfall": "अखा", "wind": "बार", "windSpeed": "बारनि गोख्रोंथि",
        "cyclone": "बारहुंखा", "thunderstorm": "अखा-बारहुंखा", "flood": "दैबाना",
        "heatwave": "दुंग्रा बार", "earthquake": "बांग्रिं", "warning": "हुसियार"
    },
    "doi": {  # Dogri
        "tagline": "भारत लेई एआई मौसम ते आपदा जानकारी",
        "overview": "अवलोकन", "globe": "लाइव ग्लोब", "forecast": "मौसम दा हाल",
        "alerts": "चेतावनी केंद्र", "climate": "जलवायु विशलेषण", "agriculture": "खेती मौसम",
        "aviation": "विमानन", "marine": "समुंदरी मौसम", "cityMonitor": "स्मार्ट शैहर",
        "dataLab": "डाटा ते लर्निंग लैब", "modelLab": "मॉडल लैब", "dashboard": "मेरा डैशबोर्ड",
        "settings": "सैटिंग्स", "logout": "साइन आउट", "createAccount": "WeatherGPT खाता बनाओ",
        "fullName": "पूरा नां", "email": "ईमेल पता", "mobile": "मोबाइल नंबर",
        "password": "पासवर्ड", "confirmPassword": "पासवर्ड दी पुष्टि करो", "state": "रियासत / राज्य",
        "district": "जिला / शैहर", "preferredLanguage": "पसंदीदा बोली",
        "submitRegister": "खाता बनाओ", "loginTitle": "लागिन करो",
        "temperature": "तापमान", "humidity": "नमी", "pressure": "हवा दा दबाव",
        "rainfall": "बरखा", "wind": "हवा", "windSpeed": "हवा दी रफ्तार",
        "cyclone": "तूफान", "thunderstorm": "गरज-चमक", "flood": "हढ़",
        "heatwave": "लूह", "earthquake": "भुचाल", "warning": "चेतावनी"
    },
    "gu": {  # Gujarati
        "tagline": "ભારત માટે એઆઈ હવામાન અને આપત્તિ ગુપ્તચર માહિતી",
        "overview": "અવલોકન", "globe": "લાઇવ ગ્લોબ", "forecast": "હવામાન આગાહી",
        "alerts": "ચેતવણી કેન્દ્ર", "climate": "આબોહવા વિશ્લેષણ", "agriculture": "કૃષિ હવામાન",
        "aviation": "ઉડ્ડયન", "marine": "દરિયાઈ હવામાન", "cityMonitor": "સ્માર્ટ સિટી",
        "dataLab": "ડેટા અને લર્નિંગ લેબ", "modelLab": "મોડેલ લેબ", "dashboard": "મારું ડેશબોર્ડ",
        "settings": "સેટિંગ્સ", "logout": "સાઇન આઉટ", "createAccount": "WeatherGPT એકાઉન્ટ બનાવો",
        "fullName": "પૂરું નામ", "email": "ઈમેલ સરનામું", "mobile": "મોબાઇલ નંબર",
        "password": "પાસવર્ડ", "confirmPassword": "પાસવર્ડ પુષ્ટિ કરો", "state": "રાજ્ય",
        "district": "જિલ્લો / શહેર", "preferredLanguage": "પસંદગીની ભાષા",
        "submitRegister": "એકાઉન્ટ બનાવો", "loginTitle": "સાઇન ઇન કરો",
        "temperature": "તાપમાન", "humidity": "ભેજ", "pressure": "હવાનું દબાણ",
        "rainfall": "વરસાદ", "wind": "પવન", "windSpeed": "પવનની ગતિ",
        "cyclone": "વાવાઝોડું", "thunderstorm": "ગાજવીજ સાથે વાવાઝોડું", "flood": "પૂર",
        "heatwave": "હીટવેવ / લૂ", "earthquake": "ભૂકંપ", "warning": "ચેતવણી"
    },
    "kn": {  # Kannada
        "tagline": "ಭಾರತಕ್ಕಾಗಿ ಎಐ ಹವಾಮಾನ ಮತ್ತು ವಿಪತ್ತು ಮುನ್ಸೂಚನೆ ಮಾಹಿತಿ",
        "overview": "ಅವಲೋಕನ", "globe": "ಲೈವ್ ಗ್ಲೋಬ್", "forecast": "ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ",
        "alerts": "ಎಚ್ಚರಿಕೆ ಕೇಂದ್ರ", "climate": "ಹವಾಮಾನ ವಿಶ್ಲೇಷಣೆ", "agriculture": "ಕೃಷಿ ಹವಾಮಾನ",
        "aviation": "ವಾಯುಯಾನ", "marine": "ಸಮುದ್ರ ಹವಾಮಾನ", "cityMonitor": "ಸ್ಮಾರ್ಟ್ ನಗರ",
        "dataLab": "ಡೇಟಾ ಮತ್ತು ಲರ್ನಿಂಗ್ ಲ್ಯಾಬ್", "modelLab": "ಮಾದರಿ ಲ್ಯಾಬ್", "dashboard": "ನನ್ನ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        "settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು", "logout": "ಸೈನ್ ಔಟ್", "createAccount": "WeatherGPT ಖಾತೆ ರಚಿಸಿ",
        "fullName": "ಪೂರ್ಣ ಹೆಸರು", "email": "ಇಮೇಲ್ ವಿಳಾಸ", "mobile": "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ",
        "password": "ಪಾಸ್‌ವರ್ಡ್", "confirmPassword": "ಪಾಸ್‌ವರ್ಡ್ ದೃಢೀಕರಿಸಿ", "state": "ರಾಜ್ಯ",
        "district": "ಜಿಲ್ಲೆ / ನಗರ", "preferredLanguage": "ಆದ್ಯತೆಯ ಭಾಷೆ",
        "submitRegister": "ಖಾತೆ ತೆರೆಯಿರಿ", "loginTitle": "ಸೈನ್ ಇನ್ ಮಾಡಿ",
        "temperature": "ತಾಪಮಾನ", "humidity": "ಆರ್ದ್ರತೆ", "pressure": "ವಾಯುಭಾರ",
        "rainfall": "ಮಳೆ", "wind": "ಗಾಳಿ", "windSpeed": "ಗಾಳಿಯ ವೇಗ",
        "cyclone": "ಚಂಡಮಾರುತ", "thunderstorm": "ಗುಡುಗು ಸಹಿತ ಮಳೆ", "flood": "ಪ್ರವಾಹ",
        "heatwave": "ಶಾಖದ ಅಲೆ", "earthquake": "ಭೂಕಂಪ", "warning": "ಎಚ್ಚರಿಕೆ"
    },
    "ks": {  # Kashmiri
        "tagline": "ہِندوستان خٲطرٕ اے۔آئی موسم تہٕ آفَتھ حِکمتِ عملی",
        "overview": "جٲیزٕ", "globe": "لائیو گلوب", "forecast": "موسمی پیشن گوئی",
        "alerts": "خَبردار مَرکز", "climate": "آب وہَوا تَجزیہٕ", "agriculture": "زِرعی موسم",
        "aviation": "ہَوائی سَفَر", "marine": "سَمندری موسم", "cityMonitor": "سمارٹ شَہَر",
        "dataLab": "ڈیٹا تہٕ لرننگ لیب", "modelLab": "ماڈل لیب", "dashboard": "میٛون ڈیش بورڈ",
        "settings": "ترتیبات", "logout": "لاگ آؤٹ", "createAccount": "WeatherGPT کھاتہٕ بناویو",
        "fullName": "پوٗرٕ ناو", "email": "ای میل", "mobile": "موبائل نمبر",
        "password": "پاس ورڈ", "confirmPassword": "پاس ورڈ تصدیق", "state": "رِیاسَتھ",
        "district": "ضلعہٕ / شَہَر", "preferredLanguage": "پَسندیدہ زَبان",
        "submitRegister": "کھاتہٕ بناویو", "loginTitle": "داخل گژھیو",
        "temperature": "دَرجہِ حرارَت", "humidity": "نَمی", "pressure": "ہَوا دَباو",
        "rainfall": "رُود", "wind": "ہَوا", "windSpeed": "ہَوا رفتار",
        "cyclone": "طوفان", "thunderstorm": "گرَج چَمک", "flood": "سیلاب",
        "heatwave": "لُو / تَپش", "earthquake": "بُنیُل", "warning": "خَبرداری"
    },
    "kok": {  # Konkani
        "tagline": "भारता खातीर एआय हवामान आनी आपत्ती म्हायती",
        "overview": "नदर", "globe": "थेट ग्लोब", "forecast": "हवामान अदमास",
        "alerts": "शिटकावणी केंद्र", "climate": "हवामान विस्लेषण", "agriculture": "शेतकाम हवामान",
        "aviation": "विमान येरादारी", "marine": "दर्या हवामान", "cityMonitor": "स्मार्ट शॅर",
        "dataLab": "डेटा आनी शिकप लॅब", "modelLab": "मॉडेल लॅब", "dashboard": "म्हजो डॅशबोर्ड",
        "settings": "मांडणी", "logout": "साइन आउट", "createAccount": "WeatherGPT खातें तयार करात",
        "fullName": "पुराय नांव", "email": "ईमेल पत्तो", "mobile": "मोबाईल नंबर",
        "password": "पासवर्ड", "confirmPassword": "पासवर्ड खात्री करात", "state": "राज्य",
        "district": "जिल्लो / शॅर", "preferredLanguage": "आवडती भास",
        "submitRegister": "खातें सुरू करात", "loginTitle": "भितर सरा",
        "temperature": "तापमान", "humidity": "दमटसाण", "pressure": "हवेचो दाब",
        "rainfall": "पावस", "wind": "वारो", "windSpeed": "वाऱ्याचो वेग",
        "cyclone": "वादळ", "thunderstorm": "गडगडाटी पावस", "flood": "हुंवार",
        "heatwave": "उश्णतेची ल्हchannel", "earthquake": "भूंयकांप", "warning": "शिटकावणी"
    },
    "mai": {  # Maithili
        "tagline": "भारतक लेल एआई मौसम आ आपदा सूचना प्रणाली",
        "overview": "अवलोकन", "globe": "लाइव ग्लोब", "forecast": "मौसम पूर्वानुमान",
        "alerts": "चेतावनी केंद्र", "climate": "जलवायु विश्लेषण", "agriculture": "कृषि मौसम",
        "aviation": "विमानन", "marine": "समुद्री मौसम", "cityMonitor": "स्मार्ट शहर",
        "dataLab": "डेटा आ लर्निंग लैब", "modelLab": "मॉडल लैब", "dashboard": "हमर डैशबोर्ड",
        "settings": "सेटिंग्स", "logout": "साइन आउट", "createAccount": "WeatherGPT खाता बनाउ",
        "fullName": "पूरा नाम", "email": "ईमेल पता", "mobile": "मोबाइल नंबर",
        "password": "पासवर्ड", "confirmPassword": "पासवर्डक पुष्टि करू", "state": "राज्य",
        "district": "जिला / शहर", "preferredLanguage": "पसंदीदा भाषा",
        "submitRegister": "खाता बनाउ", "loginTitle": "साइन इन करू",
        "temperature": "तापमान", "humidity": "आर्द्रता", "pressure": "वायुदाब",
        "rainfall": "बरखा", "wind": "हवा", "windSpeed": "हवाक गति",
        "cyclone": "चक्रवात", "thunderstorm": "वज्रपात आ मेघगर्जन", "flood": "बाढ़ि",
        "heatwave": "लू / गरम हवा", "earthquake": "भूकंप", "warning": "चेतावनी"
    },
    "ml": {  # Malayalam
        "tagline": "ഇന്ത്യയ്ക്കായുള്ള എഐ കാലാവസ്ഥാ-ദുരന്ത നിവാരണ വിവരങ്ങൾ",
        "overview": "അവലോകനം", "globe": "ലൈവ് ഗ്ലോബ്", "forecast": "കാലാവസ്ഥാ പ്രവചനം",
        "alerts": "മുന്നറിയിപ്പ് കേന്ദ്രം", "climate": "കാലാവസ്ഥാ വിശകലനം", "agriculture": "കാർഷിക കാലാവസ്ഥ",
        "aviation": "വ്യോമയാനം", "marine": "സമുദ്ര കാലാവസ്ഥ", "cityMonitor": "സ്മാർട്ട് സിറ്റി",
        "dataLab": "ഡാറ്റ & ലേണിംഗ് ലാബ്", "modelLab": "മോഡൽ ലാബ്", "dashboard": "എന്റെ ഡാഷ്‌ബോർഡ്",
        "settings": "ക്രമീകരണങ്ങൾ", "logout": "സൈൻ ഔട്ട്", "createAccount": "WeatherGPT അക്കൗണ്ട് തുറക്കൂ",
        "fullName": "പൂർണ്ണമായ പേര്", "email": "ഇമെയിൽ വിലാസം", "mobile": "മൊബൈൽ നമ്പർ",
        "password": "പാസ്‌വേഡ്", "confirmPassword": "പാസ്‌വേഡ് ഉറപ്പാക്കുക", "state": "സംസ്ഥാനം",
        "district": "ജില്ല / നഗരം", "preferredLanguage": "തിരഞ്ഞെടുത്ത ഭാഷ",
        "submitRegister": "അക്കൗണ്ട് സൃഷ്ടിക്കുക", "loginTitle": "പ്രവേശിക്കുക",
        "temperature": "താപനില", "humidity": "ഈർപ്പം", "pressure": "വായുമർദ്ദം",
        "rainfall": "മഴ", "wind": "കാറ്റ്", "windSpeed": "കാറ്റിന്റെ വേഗത",
        "cyclone": "ചുഴലിക്കാറ്റ്", "thunderstorm": "ഇടിമിന്നൽ", "flood": "വെള്ളപ്പൊക്കം",
        "heatwave": "ഉഷ്ണതരംഗം", "earthquake": "ഭൂകമ്പം", "warning": "മുന്നറിയിപ്പ്"
    },
    "mni": {  # Manipuri / Meitei
        "tagline": "ভারতকীদমক এআই নোং-চিং অমসুং অৱাবা পাউতাক",
        "overview": "য়েংশিনবা", "globe": "লাইভ গ্লোব", "forecast": "নোং-চিংগী ৱাফম",
        "alerts": "চেকশিনৱা কেন্দ্র", "climate": "নোং-চিংগী নৈনবা", "agriculture": "লৌউ-শিংউ",
        "aviation": "এভিয়েসন", "marine": "সমুদ্রগী নোং-চিং", "cityMonitor": "স্মার্ট সহর",
        "dataLab": "ডাটা অমসুং তম্বগী লেব", "modelLab": "মডেল লেব", "dashboard": "ঐগী ড্যাশবোর্ড",
        "settings": "সেটিংস", "logout": "থোকপা", "createAccount": "WeatherGPT একাউন্ট শেম্মু",
        "fullName": "অচুম্বা মিং", "email": "ইমেল", "mobile": "মোবাইল নম্বর",
        "password": "পাসওয়ার্ড", "confirmPassword": "পাসওয়ার্ড চেতীং তৌ", "state": "রাজ্য",
        "district": "জিল্লা / সহর", "preferredLanguage": "পাম্বা লোন",
        "submitRegister": "একাউন্ট হাংদোকউ", "loginTitle": "চংবা",
        "temperature": "অশাবা / অইংবা", "humidity": "অশোৎপা", "pressure": "নুংশিৎকী নম্বদা",
        "rainfall": "নোং চুরা", "wind": "নুংশিৎ", "windSpeed": "নুংশিৎকী য়াংবা",
        "cyclone": "নোংলৈ", "thunderstorm": "নোংথিংজিল", "flood": "ঈচাউ",
        "heatwave": "অশাবা ঈচেল", "earthquake": "য়ুহা হাবা", "warning": "চেকশিনৱা"
    },
    "mr": {  # Marathi
        "tagline": "भारतासाठी एआय हवामान आणि आपत्ती बुद्धिमत्ता",
        "overview": "आढावा", "globe": "थेट ग्लोब", "forecast": "हवामान अंदाज",
        "alerts": "इशारा केंद्र", "climate": "हवामान विश्लेषण", "agriculture": "कृषी हवामान",
        "aviation": "विमान वाहतूक", "marine": "सागरी हवामान", "cityMonitor": "स्मार्ट शहर",
        "dataLab": "डेटा आणि लर्निंग लॅब", "modelLab": "मॉडेल लॅब", "dashboard": "माझे डॅशबोर्ड",
        "settings": "सेटिंग्ज", "logout": "साइन आउट", "createAccount": "WeatherGPT खाते तयार करा",
        "fullName": "पूर्ण नाव", "email": "ईमेल पत्ता", "mobile": "मोबाइल नंबर",
        "password": "पासवर्ड", "confirmPassword": "पासवर्ड पुष्टी करा", "state": "राज्य",
        "district": "जिल्हा / शहर", "preferredLanguage": "पसंतीची भाषा",
        "submitRegister": "खाते उघडा", "loginTitle": "साइन इन करा",
        "temperature": "तापमान", "humidity": "आर्द्रता", "pressure": "हवेचा दाब",
        "rainfall": "पाऊस", "wind": "वारा", "windSpeed": "वाऱ्याचा वेग",
        "cyclone": "चक्रीवादळ", "thunderstorm": "वादळी पाऊस आणि विजा", "flood": "पूर",
        "heatwave": "उष्णतेची लाट", "earthquake": "भूकंप", "warning": "इशारा"
    },
    "ne": {  # Nepali
        "tagline": "भारतका लागि एआई मौसम र विपद् पूर्वसूचना",
        "overview": "सिंहावलोकन", "globe": "प्रत्यक्ष ग्लोब", "forecast": "मौसम पूर्वानुमान",
        "alerts": "सचेतना केन्द्र", "climate": "जलवायु विश्लेषण", "agriculture": "कृषि मौसम",
        "aviation": "उड्डयन", "marine": "समुद्री मौसम", "cityMonitor": "स्मार्ट सहर",
        "dataLab": "डेटा र लर्निङ ल्याब", "modelLab": "मोडेल ल्याब", "dashboard": "मेरो ड्यासबोर्ड",
        "settings": "सेटिङहरू", "logout": "साइन आउट", "createAccount": "WeatherGPT खाता बनाउनुहोस्",
        "fullName": "पूरा नाम", "email": "इमेल ठेगाना", "mobile": "मोबाइल नम्बर",
        "password": "पासवर्ड", "confirmPassword": "पासवर्ड पुष्टि गर्नुहोस्", "state": "राज्य",
        "district": "जिल्ला / सहर", "preferredLanguage": "रोजेको भाषा",
        "submitRegister": "खाता खोल्नुहोस्", "loginTitle": "साइन इन गर्नुहोस्",
        "temperature": "तापक्रम", "humidity": "आर्द्रता", "pressure": "वायुमण्डलीय चाप",
        "rainfall": "वर्षा", "wind": "हावा", "windSpeed": "हावाको गति",
        "cyclone": "चक्रवात / हुरी", "thunderstorm": "चट्याङ र मेघगर्जन", "flood": "बाढी",
        "heatwave": "लु / तातो हावा", "earthquake": "भूकम्प", "warning": "चेतावनी"
    },
    "or": {  # Odia
        "tagline": "ଭାରତ ପାଇଁ ଏଆଇ ପାଣିପାଗ ଏବଂ ବିପର୍ଯ୍ୟୟ ସୂଚନା",
        "overview": "ସମୀକ୍ଷା", "globe": "ଲାଇଭ୍ ଗ୍ଲୋବ୍", "forecast": "ପାଣିପାଗ ପୂର୍ବାନୁମାନ",
        "alerts": "ସତର୍କତା କେନ୍ଦ୍ର", "climate": "ଜଳବାୟୁ ବିଶ୍ଳେଷଣ", "agriculture": "କୃଷି ପାଣିପାଗ",
        "aviation": "ବିମାନ ଚଳାଚଳ", "marine": "ସାମୁଦ୍ରିକ ପାଣିପାଗ", "cityMonitor": "ସ୍ମାର୍ଟ ସହର",
        "dataLab": "ଡାଟା ଏବଂ ଲର୍ଣ୍ଣିଂ ଲ୍ୟାବ୍", "modelLab": "ମଡେଲ୍ ଲ୍ୟାବ୍", "dashboard": "ମୋର ଡ୍ୟାସବୋର୍ଡ",
        "settings": "ସେଟିଙ୍ଗସ୍", "logout": "ସାଇନ୍ ଆଉଟ୍", "createAccount": "WeatherGPT ଖାତା ଖୋଲନ୍ତୁ",
        "fullName": "ପୂରା ନାମ", "email": "ଇମେଲ୍ ଠିକଣା", "mobile": "ମୋବାଇଲ୍ ନମ୍ବର",
        "password": "ପାସୱାର୍ଡ", "confirmPassword": "ପାସୱାର୍ଡ ନିଶ୍ଚିତ କରନ୍ତୁ", "state": "ରାଜ୍ୟ",
        "district": "ଜିଲ୍ଲା / ସହର", "preferredLanguage": "ପସନ୍ଦର ଭାଷା",
        "submitRegister": "ଖାତା ସୃଷ୍ଟି କରନ୍ତୁ", "loginTitle": "ସାଇନ୍ ଇନ୍ କରନ୍ତୁ",
        "temperature": "ତାପମାତ୍ରା", "humidity": "ଆର୍ଦ୍ରତା", "pressure": "ବାୟୁଚାପ",
        "rainfall": "ବର୍ଷା", "wind": "ପବନ", "windSpeed": "ପବନର ବେଗ",
        "cyclone": "ବାତ୍ୟା", "thunderstorm": "ଘଡ଼ଘଡ଼ି ଏବଂ ବର୍ଷା", "flood": "ବନ୍ୟା",
        "heatwave": "ଗ୍ରୀଷ୍ମ ପ୍ରବାହ", "earthquake": "ଭୂମିକମ୍ପ", "warning": "ସତର୍କ ସୂଚନା"
    },
    "pa": {  # Punjabi
        "tagline": "ਭਾਰਤ ਲਈ ਏਆਈ ਮੌਸਮ ਅਤੇ ਆਫ਼ਤ ਖੁਫ਼ੀਆ ਜਾਣਕਾਰੀ",
        "overview": "ਸੰਖੇਪ", "globe": "ਲਾਈਵ ਗਲੋਬ", "forecast": "ਮੌਸਮ ਭਵਿੱਖਬਾਣੀ",
        "alerts": "ਚੇਤਾਵਨੀ ਕੇਂਦਰ", "climate": "ਜਲਵਾਯੂ ਵਿਸ਼ਲੇਸ਼ਣ", "agriculture": "ਖੇਤੀਬਾੜੀ ਮੌਸਮ",
        "aviation": "ਹਵਾਬਾਜ਼ੀ", "marine": "ਸਮੁੰਦਰੀ ਮੌਸਮ", "cityMonitor": "ਸਮਾਰਟ ਸ਼ਹਿਰ",
        "dataLab": "ਡਾਟਾ ਅਤੇ ਲਰਨਿੰਗ ਲੈਬ", "modelLab": "ਮਾਡਲ ਲੈਬ", "dashboard": "ਮੇਰਾ ਡੈਸ਼ਬੋਰਡ",
        "settings": "ਸੈਟਿੰਗਾਂ", "logout": "ਸਾਈਨ ਆਉਟ", "createAccount": "WeatherGPT ਖਾਤਾ ਬਣਾਓ",
        "fullName": "ਪੂਰਾ ਨਾਮ", "email": "ਈਮੇਲ ਪਤਾ", "mobile": "ਮੋਬਾਈਲ ਨੰਬਰ",
        "password": "ਪਾਸਵਰਡ", "confirmPassword": "ਪਾਸਵਰਡ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ", "state": "ਰਾਜ",
        "district": "ਜ਼ਿਲ੍ਹਾ / ਸ਼ਹਿਰ", "preferredLanguage": "ਪਸੰਦੀਦਾ ਭਾਸ਼ਾ",
        "submitRegister": "ਖਾਤਾ ਬਣਾਓ", "loginTitle": "ਲਾਗਇਨ ਕਰੋ",
        "temperature": "ਤਾਪਮਾਨ", "humidity": "ਨਮੀ", "pressure": "ਹਵਾ ਦਾ ਦਬਾਅ",
        "rainfall": "ਮੀਂਹ", "wind": "ਹਵਾ", "windSpeed": "ਹਵਾ ਦੀ ਰਫ਼ਤਾਰ",
        "cyclone": "ਤੂਫ਼ਾਨ / ਚੱਕਰਵਾਤ", "thunderstorm": "ਗਰਜ ਚਮਕ ਨਾਲ ਮੀਂਹ", "flood": "ਹੜ੍ਹ",
        "heatwave": "ਲੂਹ / ਗਰਮੀ ਦੀ ਲਹਿਰ", "earthquake": "ਭੂਚਾਲ", "warning": "ਚੇਤਾਵਨੀ"
    },
    "sa": {  # Sanskrit
        "tagline": "भारतस्य कृते कृत्रिमबुद्धियुक्त-ऋतु-आपत्-सूचना",
        "overview": "अवलोकनम्", "globe": "प्रत्यक्ष-भूगोलकम्", "forecast": "ऋतुपूर्वानुमानम्",
        "alerts": "चेतावनी-केन्द्रम्", "climate": "जलवायु-विश्लेषणम्", "agriculture": "कृषि-ऋतुविज्ञानम्",
        "aviation": "विमानयानम्", "marine": "सामुद्रिक-ऋतुः", "cityMonitor": "स्मार्ट-नगरम्",
        "dataLab": "दत्तांश-अध्ययन-प्रकोष्ठः", "modelLab": "प्रतिदर्श-प्रकोष्ठः", "dashboard": "मम फलकम्",
        "settings": "विन्यासाः", "logout": "निर्गमनम्", "createAccount": "WeatherGPT खातं रचयतु",
        "fullName": "पूर्णं नाम", "email": "विद्युत्पत्र-सङ्केतः", "mobile": "दूरवाणी-सङ्ख्या",
        "password": "गुप्तपदम्", "confirmPassword": "गुप्तपद-पुष्टिः", "state": "राज्यम्",
        "district": "मण्डलम् / नगरम्", "preferredLanguage": "अभिमता भाषा",
        "submitRegister": "खातं रचयतु", "loginTitle": "प्रवेशः",
        "temperature": "तापमानम्", "humidity": "आर्द्रता", "pressure": "वायुदाबः",
        "rainfall": "वृष्टिः", "wind": "वायुः", "windSpeed": "वायुवेगः",
        "cyclone": "चक्रवातः", "thunderstorm": "विद्युत्-गर्जनम्", "flood": "जलप्लावनम्",
        "heatwave": "उष्णतरङ्गः", "earthquake": "भूकम्पः", "warning": "सचेतता"
    },
    "sat": {  # Santali
        "tagline": "ᱵᱷᱟᱨᱚᱛ ᱞᱟᱹᱜᱤᱫ ᱮᱟᱭ ᱦᱚᱭ-ᱦᱤᱥᱤᱫ ᱟᱨ ᱟᱯᱚᱛ ᱵᱟᱰᱟᱭ",
        "overview": "ᱧᱮᱞ", "globe": "ᱞᱟᱭᱤᱵᱽ ᱜᱞᱳᱵᱽ", "forecast": "ᱦᱚᱭ-ᱦᱤᱥᱤᱫ ᱞᱟᱦᱟ ᱞᱟᱹᱭ",
        "alerts": "ᱦᱩᱥᱤᱭᱟᱹᱨ ᱛᱟᱞᱢᱟ", "climate": "ᱦᱚᱭ-ᱫᱟᱜ ᱵᱤᱪᱟᱹᱨ", "agriculture": "ᱪᱟᱥ-ᱵᱟᱥ",
        "aviation": "ᱩᱰᱟᱹᱱ ᱜᱟᱹᱰᱤ", "marine": "ᱫᱚᱨᱭᱟ ᱦᱚᱭ-ᱦᱤᱥᱤᱫ", "cityMonitor": "ᱥᱢᱟᱨᱴ ᱵᱟᱡᱟᱨ",
        "dataLab": "ᱰᱟᱴᱟ ᱟᱨ ᱪᱮᱫᱚᱜ ᱞᱮᱵᱽ", "modelLab": "ᱢᱚᱰᱮᱞ ᱞᱮᱵᱽ", "dashboard": "ᱤᱧᱟᱜ ᱰᱮᱥᱵᱳᱨᱰ",
        "settings": "ᱥᱟᱡᱟᱣ", "logout": "ᱵᱟᱦᱨᱮ", "createAccount": "WeatherGPT ᱠᱷᱟᱛᱟ ᱵᱮᱱᱟᱣ",
        "fullName": "ᱯᱩᱨᱟᱹ ᱧᱩᱛᱩᱢ", "email": "ᱤᱢᱮᱞ", "mobile": "ᱢᱳᱵᱟᱭᱤᱞ ᱱᱚᱢᱵᱚᱨ",
        "password": "ᱯᱟᱥᱣᱟᱨᱰ", "confirmPassword": "ᱯᱟᱥᱣᱟᱨᱰ ᱴᱷᱟᱹᱣᱠᱟᱹ", "state": "ᱯᱚᱱᱚᱛ",
        "district": "ᱡᱤᱞᱟᱹ / ᱵᱟᱡᱟᱨ", "preferredLanguage": "ᱠᱩᱥᱤᱭᱟᱜ ᱯᱟᱹᱨᱥᱤ",
        "submitRegister": "ᱠᱷᱟᱛᱟ ᱵᱮᱱᱟᱣ", "loginTitle": "ᱵᱚᱞᱚᱱ",
        "temperature": "ᱞᱚᱞᱚ", "humidity": "ᱩᱫᱽᱜᱟᱹᱨ", "pressure": "ᱦᱚᱭ  হেঁচ",
        "rainfall": "ᱫᱟᱜ", "wind": "ᱦᱚᱭ", "windSpeed": "ᱦᱚᱭ ᱜᱟᱹᱛ",
        "cyclone": "ᱵᱟᱹᱨᱰᱩ", "thunderstorm": "ᱫᱟᱜ-ᱵᱤᱡᱽᱞᱤ", "flood": "ᱵᱟᱱ",
        "heatwave": "ᱞᱚᱞᱚ ᱦᱚᱭ", "earthquake": "ᱚᱛ ᱞᱟᱲᱟᱣ", "warning": "ᱦᱩᱥᱤᱭᱟᱹᱨ"
    },
    "sd": {  # Sindhi (Perso-Arabic script, RTL)
        "tagline": "ڀارت لاءِ اي آءِ موسم ۽ آفت جي معلومات",
        "overview": "جائزو", "globe": "لائيو گلوب", "forecast": "موسم جي اڳڪٿي",
        "alerts": "خبرداري مرڪز", "climate": "آبهوا تجزيو", "agriculture": "زرعي موسم",
        "aviation": "هوائي اڏام", "marine": "سامونڊي موسم", "cityMonitor": "سمارٽ شهر",
        "dataLab": "ڊيٽا ۽ سکيا ليب", "modelLab": "ماڊل ليب", "dashboard": "منهنجو ڊيش بورڊ",
        "settings": "سيٽنگون", "logout": "لاگ آئوٽ", "createAccount": "WeatherGPT کاتو ٺاهيو",
        "fullName": "پورو نالو", "email": "اي ميل پتو", "mobile": "موبائل نمبر",
        "password": "پاس ورڊ", "confirmPassword": "پاس ورڊ جي تصديق", "state": "صوبو / رياست",
        "district": "ضلعو / شهر", "preferredLanguage": "پسنديده ٻولي",
        "submitRegister": "کاتو ٺاهيو", "loginTitle": "داخل ٿيو",
        "temperature": "گرمي پد", "humidity": "گهم", "pressure": "هوا جو دٻاءُ",
        "rainfall": "برسات", "wind": "هوا", "windSpeed": "هوا جي رفتار",
        "cyclone": "طوفان", "thunderstorm": "گجگوڙ ۽ وڄ", "flood": "ٻوڏ",
        "heatwave": "گرم هوا / لوءِ", "earthquake": "زلزلو", "warning": "خبرداري"
    },
    "ta": {  # Tamil
        "tagline": "இந்தியாவுக்கான ஏஐ வானிலை மற்றும் பேரிடர் முன்னெச்சரிக்கை",
        "overview": "மேலோட்டம்", "globe": "நேரலை பூகோளம்", "forecast": "வானிலை முன்னறிவிப்பு",
        "alerts": "எச்சரிக்கை மையம்", "climate": "காலநிலை பகுப்பாய்வு", "agriculture": "விவசாய வானிலை",
        "aviation": "விமானப் போக்குவரத்து", "marine": "கடல் வானிலை", "cityMonitor": "ஸ்மார்ட் நகரம்",
        "dataLab": "தரவு மற்றும் கற்றல் கூடம்", "modelLab": "மாதிரி கூடம்", "dashboard": "என் முகப்பு",
        "settings": "அமைப்புகள்", "logout": "வெளியேறு", "createAccount": "WeatherGPT கணக்கை உருவாக்கவும்",
        "fullName": "முழுப் பெயர்", "email": "மின்னஞ்சல் முகவரி", "mobile": "மொபைல் எண்",
        "password": "கடவுச்சொல்", "confirmPassword": "கடவுச்சொல்லை உறுதிசெய்", "state": "மாநிலம்",
        "district": "மாவட்டம் / நகரம்", "preferredLanguage": "விருப்பமான மொழி",
        "submitRegister": "கணக்கை உருவாக்கு", "loginTitle": "உள்நுழையவும்",
        "temperature": "வெப்பநிலை", "humidity": "ஈரப்பதம்", "pressure": "காற்றழுத்தம்",
        "rainfall": "மழைப்பொழிவு", "wind": "காற்று", "windSpeed": "காற்றின் வேகம்",
        "cyclone": "புயல்", "thunderstorm": "இடி மின்னலுடன் கூடிய மழை", "flood": "வெள்ளம்",
        "heatwave": "வெப்ப அலை", "earthquake": "நிலநடுக்கம்", "warning": "எச்சரிக்கை"
    },
    "te": {  # Telugu
        "tagline": "భారతదేశం కోసం ఏఐ వాతావరణ మరియు విపత్తు నిఘా సమాచారం",
        "overview": "సమీక్ష", "globe": "లైవ్ గ్లోబ్", "forecast": "వాతావరణ సూచన",
        "alerts": "హెచ్చరికల కేంద్రం", "climate": "శీతోష్ణస్థితి విశ్లేషణ", "agriculture": "వ్యవసాయ వాతావరణం",
        "aviation": "విమానయానం", "marine": "సముద్ర వాతావరణం", "cityMonitor": "స్మార్ట్ నగరం",
        "dataLab": "డేటా & లెర్నింగ్ ల్యాబ్", "modelLab": "మోడల్ ల్యాబ్", "dashboard": "నా డాష్‌బోర్డ్",
        "settings": "సెట్టింగ్‌లు", "logout": "లాగ్ అవుట్", "createAccount": "WeatherGPT ఖాతాను సృష్టించండి",
        "fullName": "పూర్తి పేరు", "email": "ఈమెయిల్ చిరునామా", "mobile": "మొబైల్ నంబర్",
        "password": "పాస్‌వర్డ్", "confirmPassword": "పాస్‌వర్డ్ నిర్ధారించండి", "state": "రాష్ట్రం",
        "district": "జిల్లా / నగరం", "preferredLanguage": "ప్రాధాన్య భాష",
        "submitRegister": "ఖాతా సృష్టించు", "loginTitle": "సైన్ ఇన్ చేయండి",
        "temperature": "ఉష్ణోగ్రత", "humidity": "తేమ శాతం", "pressure": "గాలి పీడనం",
        "rainfall": "వర్షపాతం", "wind": "గాలి", "windSpeed": "గాలి వేగం",
        "cyclone": "తుఫాను", "thunderstorm": "ఉరుములు మెరుపులతో కూడిన వర్షం", "flood": "వరద",
        "heatwave": "వడగాల్పులు", "earthquake": "భూకంపం", "warning": "హెచ్చరిక"
    },
    "ur": {  # Urdu (Perso-Arabic script, RTL)
        "tagline": "بھارت کے لیے اے آئی موسم اور قدرتی آفات کی ذہین معلومات",
        "overview": "جائزہ", "globe": "لائیو گلوب", "forecast": "موسم کی پیش گوئی",
        "alerts": "انتباہی مرکز", "climate": "آب و ہوا کا تجزیہ", "agriculture": "زرعی موسم",
        "aviation": "ہوا بازی", "marine": "سمندری موسم", "cityMonitor": "سمارٹ سٹی",
        "dataLab": "ڈیٹا اور لرننگ لیب", "modelLab": "ماڈل لیب", "dashboard": "میرا ڈیش بورڈ",
        "settings": "ترتیبات", "logout": "سائن آؤٹ", "createAccount": "WeatherGPT اکاؤنٹ بنائیں",
        "fullName": "پورا نام", "email": "ای میل پتہ", "mobile": "موبائل نمبر",
        "password": "پاس ورڈ", "confirmPassword": "پاس ورڈ کی تصدیق کریں", "state": "ریاست",
        "district": "ضلع / شہر", "preferredLanguage": "پسندیدہ زبان",
        "submitRegister": "اکاؤنٹ بنائیں", "loginTitle": "سائن ان کریں",
        "temperature": "درجہ حرارت", "humidity": "نمی", "pressure": "ہوا کا دباؤ",
        "rainfall": "بارش", "wind": "ہوا", "windSpeed": "ہوا کی رفتار",
        "cyclone": "سمندری طوفان", "thunderstorm": "گرج چمک اور آندھی", "flood": "سیلاب",
        "heatwave": "لو / ہیٹ ویو", "earthquake": "زلزلہ", "warning": "انتباہ"
    }
}

def create_lang_dict(base_dict, overrides):
    """Deep clone and replace mapped keys with language specific words."""
    result = json.loads(json.dumps(base_dict))
    # Brand
    if "tagline" in overrides:
        result["brand"]["tagline"] = overrides["tagline"]
    
    # Nav mappings
    for k in ("overview", "globe", "forecast", "alerts", "climate", "agriculture", 
              "aviation", "marine", "cityMonitor", "dataLab", "modelLab", "dashboard", 
              "settings", "logout"):
        if k in overrides:
            result["nav"][k] = overrides[k]
            
    # Auth mappings
    for k in ("createAccount", "fullName", "email", "mobile", "password", "confirmPassword",
              "state", "district", "preferredLanguage", "submitRegister", "loginTitle"):
        if k in overrides:
            result["auth"][k] = overrides[k]
            
    # Weather mappings
    for k in ("temperature", "humidity", "pressure", "rainfall", "wind", "windSpeed", "forecast"):
        if k in overrides:
            result["weather"][k] = overrides[k]
            
    # Alert mappings
    for k in ("warning", "cyclone", "thunderstorm", "flood", "heatwave", "earthquake"):
        if k in overrides:
            result["alerts"][k] = overrides[k]
            
    return result

def main():
    # 1. Write English
    (DEST / "en.json").write_text(json.dumps(EN, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote en.json")

    # 2. Write Hindi
    (DEST / "hi.json").write_text(json.dumps(HI, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote hi.json")

    # 3. Write other 21 Indian languages
    for code, terms in INDIAN_LANGUAGES.items():
        data = create_lang_dict(EN, terms)
        (DEST / f"{code}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {code}.json")

    print(f"Successfully generated all 23 language dictionaries in {DEST}")

if __name__ == "__main__":
    main()
