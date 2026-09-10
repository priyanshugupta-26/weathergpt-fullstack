/**
 * WeatherGPT Complete Indian Language (Eighth Schedule + English) i18n Architecture
 * Supporting 22 Official Indian Languages + English (23 total)
 */

import en from "./i18n/en.json";
import hi from "./i18n/hi.json";
import as from "./i18n/as.json";
import bn from "./i18n/bn.json";
import brx from "./i18n/brx.json";
import doi from "./i18n/doi.json";
import gu from "./i18n/gu.json";
import kn from "./i18n/kn.json";
import ks from "./i18n/ks.json";
import kok from "./i18n/kok.json";
import mai from "./i18n/mai.json";
import ml from "./i18n/ml.json";
import mni from "./i18n/mni.json";
import mr from "./i18n/mr.json";
import ne from "./i18n/ne.json";
import or_ from "./i18n/or.json";
import pa from "./i18n/pa.json";
import sa from "./i18n/sa.json";
import sat from "./i18n/sat.json";
import sd from "./i18n/sd.json";
import ta from "./i18n/ta.json";
import te from "./i18n/te.json";
import ur from "./i18n/ur.json";

export interface LanguageInfo {
  code: string;
  name: string;
  nativeName: string;
  dir: "ltr" | "rtl";
  speechLocale: string;
}

export const LANGUAGES: LanguageInfo[] = [
  { code: "en", name: "English", nativeName: "English", dir: "ltr", speechLocale: "en-IN" },
  { code: "hi", name: "Hindi", nativeName: "हिन्दी", dir: "ltr", speechLocale: "hi-IN" },
  { code: "as", name: "Assamese", nativeName: "অসমীয়া", dir: "ltr", speechLocale: "as-IN" },
  { code: "bn", name: "Bengali", nativeName: "বাংলা", dir: "ltr", speechLocale: "bn-IN" },
  { code: "brx", name: "Bodo", nativeName: "बड़ो", dir: "ltr", speechLocale: "hi-IN" },
  { code: "doi", name: "Dogri", nativeName: "डोगरी", dir: "ltr", speechLocale: "hi-IN" },
  { code: "gu", name: "Gujarati", nativeName: "ગુજરાતી", dir: "ltr", speechLocale: "gu-IN" },
  { code: "kn", name: "Kannada", nativeName: "ಕನ್ನಡ", dir: "ltr", speechLocale: "kn-IN" },
  { code: "ks", name: "Kashmiri", nativeName: "कॉशुर / کٲشُر", dir: "rtl", speechLocale: "ur-IN" },
  { code: "kok", name: "Konkani", nativeName: "कोंकणी", dir: "ltr", speechLocale: "kok-IN" },
  { code: "mai", name: "Maithili", nativeName: "मैथिली", dir: "ltr", speechLocale: "hi-IN" },
  { code: "ml", name: "Malayalam", nativeName: "മലയാളം", dir: "ltr", speechLocale: "ml-IN" },
  { code: "mni", name: "Manipuri", nativeName: "মৈতৈলোন্ / Manipuri", dir: "ltr", speechLocale: "bn-IN" },
  { code: "mr", name: "Marathi", nativeName: "मराठी", dir: "ltr", speechLocale: "mr-IN" },
  { code: "ne", name: "Nepali", nativeName: "नेपाली", dir: "ltr", speechLocale: "ne-NP" },
  { code: "or", name: "Odia", nativeName: "ଓଡ଼ିଆ", dir: "ltr", speechLocale: "or-IN" },
  { code: "pa", name: "Punjabi", nativeName: "ਪੰਜਾਬੀ", dir: "ltr", speechLocale: "pa-IN" },
  { code: "sa", name: "Sanskrit", nativeName: "संस्कृतम्", dir: "ltr", speechLocale: "sa-IN" },
  { code: "sat", name: "Santali", nativeName: "ᱥᱟᱱᱛᱟᱲᱤ", dir: "ltr", speechLocale: "hi-IN" },
  { code: "sd", name: "Sindhi", nativeName: "سنڌي / सिन्धी", dir: "rtl", speechLocale: "sd-IN" },
  { code: "ta", name: "Tamil", nativeName: "தமிழ்", dir: "ltr", speechLocale: "ta-IN" },
  { code: "te", name: "Telugu", nativeName: "తెలుగు", dir: "ltr", speechLocale: "te-IN" },
  { code: "ur", name: "Urdu", nativeName: "اردو", dir: "rtl", speechLocale: "ur-IN" },
];

const DICTIONARIES: Record<string, any> = {
  en,
  hi,
  as,
  bn,
  brx,
  doi,
  gu,
  kn,
  ks,
  kok,
  mai,
  ml,
  mni,
  mr,
  ne,
  or: or_,
  pa,
  sa,
  sat,
  sd,
  ta,
  te,
  ur,
};

/**
 * Get language info object by code
 */
export function getLanguageInfo(code: string): LanguageInfo {
  return LANGUAGES.find((l) => l.code === code) || LANGUAGES[0];
}

/**
 * Check if language is RTL
 */
export function isRTL(code: string): boolean {
  return getLanguageInfo(code).dir === "rtl";
}

/**
 * Get Speech recognition / synthesis locale
 */
export function getSpeechLocale(code: string): string {
  return getLanguageInfo(code).speechLocale;
}

/**
 * Translate a dot-separated key with strict fallback to canonical English
 * Example: t("auth.createAccount", "te")
 */
export function t(key: string, langCode = "en"): string {
  const parts = key.split(".");
  
  // 1. Try selected language
  const targetDict = DICTIONARIES[langCode] || DICTIONARIES.en;
  let val: any = targetDict;
  for (const part of parts) {
    if (val && typeof val === "object" && part in val) {
      val = val[part];
    } else {
      val = undefined;
      break;
    }
  }

  if (typeof val === "string" && val.trim() !== "") {
    return val;
  }

  // 2. Strict Fallback to English
  let fallbackVal: any = DICTIONARIES.en;
  for (const part of parts) {
    if (fallbackVal && typeof fallbackVal === "object" && part in fallbackVal) {
      fallbackVal = fallbackVal[part];
    } else {
      fallbackVal = undefined;
      break;
    }
  }

  if (typeof fallbackVal === "string") {
    return fallbackVal;
  }

  // If even fallback isn't found, return last part of key rather than empty
  return parts[parts.length - 1];
}
