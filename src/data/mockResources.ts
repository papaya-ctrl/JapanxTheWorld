import type { OfficialResource } from "../types";

export const mockResources: OfficialResource[] = [
  {
    id: "isa-main",
    title: "Immigration Services Agency of Japan",
    category: "Immigration",
    description:
      "Official immigration procedures, notices, and support information.",
    url: "https://www.moj.go.jp/isa/",
  },
  {
    id: "hello-work",
    title: "Hello Work",
    category: "Career",
    description:
      "Public employment support and job information in Japan.",
    url: "https://www.hellowork.mhlw.go.jp/",
  },
  {
    id: "mhlw-insurance",
    title: "Ministry of Health, Labour and Welfare",
    category: "Insurance",
    description:
      "Official information related to labor, health, and insurance systems.",
    url: "https://www.mhlw.go.jp/english/",
  },
  {
    id: "soumu-tax",
    title: "Ministry of Internal Affairs and Communications",
    category: "Tax",
    description:
      "Reference information related to local taxes and municipal administration.",
    url: "https://www.soumu.go.jp/english/",
  },
  {
    id: "city-hall-moving-guide",
    title: "Local City Hall Moving Procedures",
    category: "City Hall",
    description:
      "Use your city office website to confirm address registration steps in your area.",
    url: "https://www.japan-guide.com/e/e2220.html",
  },
  {
    id: "city-tax-helpdesk",
    title: "City Tax Support Desk",
    category: "Tax",
    description:
      "Contact your city office for the final answer about residence tax notices.",
    url: "https://www.soumu.go.jp/main_sosiki/jichi_zeisei/czaisei/czaisei_seido/ichiran08.html",
  },
  {
    id: "city-insurance-helpdesk",
    title: "City Insurance Support Desk",
    category: "Insurance",
    description:
      "Use your city office insurance desk when payment notices or categories are unclear.",
    url: "https://www.mhlw.go.jp/english/policy/health-medical/health-insurance/index.html",
  },
];
