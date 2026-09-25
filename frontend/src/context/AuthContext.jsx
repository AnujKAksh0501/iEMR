import { createContext, useContext, useEffect, useState } from "react";
import api from "@/lib/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = logged out

  useEffect(() => {
    const token = localStorage.getItem("emr_token");
    if (!token) { setUser(false); return; }
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => {
      localStorage.removeItem("emr_token");
      setUser(false);
    });
  }, []);

  const persist = (data) => {
    localStorage.setItem("emr_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const login = async (email, password) => persist((await api.post("/auth/login", { email, password })).data);
  const register = async (payload) => persist((await api.post("/auth/register", payload)).data);
  const googleLogin = async (session_id) => persist((await api.post("/auth/google", { session_id })).data);
  const logout = () => { localStorage.removeItem("emr_token"); setUser(false); };

  return (
    <AuthContext.Provider value={{ user, login, register, googleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
