import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { apiConfiguration, validateBuildConfiguration } from "./configuration";
import { authorizationHeader, clearAuthSession, getAuthSession, signIn, signOut } from "./auth";
import { analyzeDocument } from "./client";
import { AccountAccess } from "../components/AccountAccess";
import { AnalysisSessionProvider, useAnalysisSession } from "../context/AnalysisSession";
import { uploadResult } from "../test/documentFixtures";

const publicProduction = { VITE_API_BASE_URL:"https://api.example.test/api", VITE_USE_MOCK_API:"false", VITE_REQUIRE_AUTH:"true" };
const authResponse = () => new Response(JSON.stringify({ token:"a".repeat(40),expiresIn:3600,user:{id:1,username:"synthetic-user",canAnalyzeDocuments:true} }),{status:200});
const file = () => ({file:new File(["synthetic"],"document.png",{type:"image/png"}),name:"document.png",type:"image/png",size:9});

beforeEach(() => { clearAuthSession(); vi.stubEnv("VITE_USE_MOCK_API","false"); vi.stubEnv("VITE_REQUIRE_AUTH","false"); });
afterEach(() => { cleanup(); act(() => clearAuthSession()); vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.restoreAllMocks(); vi.useRealTimers(); });

describe("production public configuration",() => {
  it("accepts an explicit HTTPS backend or same-origin /api",() => {
    expect(validateBuildConfiguration(publicProduction).baseURL).toBe("https://api.example.test/api");
    expect(validateBuildConfiguration({...publicProduction,VITE_API_BASE_URL:"/api"}).baseURL).toBe("/api");
  });
  it.each(["http://api.example.test/api","https://localhost/api","https://127.0.0.1/api","https://user:password@api.example.test/api","https://api.example.test/api?token=private","//api.example.test/api"])("rejects unsafe production URL %s",baseURL => {
    expect(() => validateBuildConfiguration({...publicProduction,VITE_API_BASE_URL:baseURL})).toThrow();
  });
  it("rejects production mock mode, auth opt-out and unknown browser secrets",() => {
    expect(() => validateBuildConfiguration({...publicProduction,VITE_USE_MOCK_API:"true"})).toThrow();
    expect(() => validateBuildConfiguration({...publicProduction,VITE_REQUIRE_AUTH:"false"})).toThrow();
    expect(() => validateBuildConfiguration({...publicProduction,VITE_BACKEND_SECRET:"SYNTHETIC_PRIVATE_MARKER"})).toThrow();
    expect(() => validateBuildConfiguration({...publicProduction,VITE_API_BASE_URL:"/api"},true,true)).toThrow();
  });
  it("keeps local demo configuration separate",() => {
    expect(apiConfiguration({VITE_API_BASE_URL:"http://localhost:8000/api",VITE_USE_MOCK_API:"true"},false).useMock).toBe(true);
  });
});

describe("in-memory account access",() => {
  it("sends credentials only to login and never stores the token or password",async () => {
    const storage = vi.spyOn(Storage.prototype,"setItem");
    const fetch = vi.fn().mockResolvedValue(authResponse());vi.stubGlobal("fetch",fetch);
    await signIn("synthetic-user","SYNTHETIC_PASSWORD");
    expect(authorizationHeader()).toBe(`Token ${"a".repeat(40)}`);
    expect(getAuthSession()?.user.username).toBe("synthetic-user");
    expect(storage).not.toHaveBeenCalled();
    expect(fetch.mock.calls[0][1]).toMatchObject({credentials:"omit",cache:"no-store",referrerPolicy:"no-referrer"});
    expect(JSON.stringify(getAuthSession())).not.toContain("SYNTHETIC_PASSWORD");
    expect(JSON.stringify(getAuthSession())).not.toContain("a".repeat(40));
  });
  it("expires the browser credential without extending its lifetime",async () => {
    vi.useFakeTimers();vi.stubGlobal("fetch",vi.fn().mockResolvedValue(authResponse()));
    await signIn("synthetic-user","SYNTHETIC_PASSWORD");
    await vi.advanceTimersByTimeAsync(3600_000);
    expect(getAuthSession()).toBeNull();expect(authorizationHeader()).toBeUndefined();
  });
  it("revokes the token on logout and clears local state even on network failure",async () => {
    const fetch=vi.fn().mockResolvedValueOnce(authResponse()).mockRejectedValueOnce(new Error("PRIVATE_TRACE"));vi.stubGlobal("fetch",fetch);
    await signIn("synthetic-user","SYNTHETIC_PASSWORD");
    expect(await signOut()).toBe(false);
    expect(getAuthSession()).toBeNull();expect(authorizationHeader()).toBeUndefined();
    expect(fetch.mock.calls[1][1].headers.Authorization).toBe(`Token ${"a".repeat(40)}`);
    expect(fetch.mock.calls[1][1].body).toBe("{}");
  });
  it.each([401,403])("handles HTTP %i without exposing response details or retrying",async status => {
    const fetch=vi.fn().mockResolvedValueOnce(authResponse()).mockResolvedValueOnce(new Response(JSON.stringify({message:"PRIVATE_CREDENTIAL_TRACE"}),{status}));vi.stubGlobal("fetch",fetch);
    await signIn("synthetic-user","SYNTHETIC_PASSWORD");
    try { await analyzeDocument({documentFile:file()});throw new Error("Expected denial"); }
    catch(error) { expect(error).toMatchObject({status});expect(JSON.stringify(error)).not.toContain("PRIVATE_CREDENTIAL_TRACE"); }
    if(status===401) expect(getAuthSession()).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it("discards an in-flight document response after the account changes",async () => {
    let complete!:(response:Response)=>void;
    const fetch=vi.fn().mockResolvedValueOnce(authResponse()).mockImplementationOnce(()=>new Promise(resolve=>{complete=resolve;}));vi.stubGlobal("fetch",fetch);
    await signIn("synthetic-user","SYNTHETIC_PASSWORD");
    const pending=analyzeDocument({documentFile:file()});
    clearAuthSession();complete(new Response(JSON.stringify(uploadResult())));
    await expect(pending).rejects.toMatchObject({code:"AUTH_REQUIRED"});
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it("clears displayed analysis when signing out",async () => {
    vi.stubEnv("VITE_REQUIRE_AUTH","true");
    vi.stubGlobal("fetch",vi.fn().mockResolvedValueOnce(authResponse()).mockResolvedValueOnce(new Response("{}",{status:200})));
    await signIn("synthetic-user","SYNTHETIC_PASSWORD");
    function Probe() {
      const session=useAnalysisSession();const [id,setId]=useState("");
      return <><button onClick={()=>setId(session.put({...uploadResult(),summary:"SYNTHETIC_PRIVATE_RESULT"}))}>Seed result</button><p>{session.get(id)?.summary??"Result cleared"}</p></>;
    }
    render(<AnalysisSessionProvider><AccountAccess/><Probe/></AnalysisSessionProvider>);
    fireEvent.click(screen.getByRole("button",{name:"Seed result"}));
    expect(screen.getByText("SYNTHETIC_PRIVATE_RESULT")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"Sign out"}));
    await waitFor(()=>expect(screen.queryByText("SYNTHETIC_PRIVATE_RESULT")).not.toBeInTheDocument());
    expect(screen.getByText("Result cleared")).toBeInTheDocument();
  });
  it("provides sign-in without adding a persistent credential",async () => {
    vi.stubEnv("VITE_REQUIRE_AUTH","true");vi.stubGlobal("fetch",vi.fn().mockResolvedValue(authResponse()));
    render(<AccountAccess/>);
    fireEvent.change(screen.getByLabelText("Account name"),{target:{value:"synthetic-user"}});
    fireEvent.change(screen.getByLabelText("Password"),{target:{value:"SYNTHETIC_PASSWORD"}});
    fireEvent.click(screen.getByRole("button",{name:"Sign in"}));
    await waitFor(()=>expect(screen.getByText(/Signed in as synthetic-user/)).toBeInTheDocument());
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });
});
