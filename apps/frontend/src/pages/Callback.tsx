import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { exchangeCodeForTokens } from "../auth/cognito";

export function Callback() {
  const [searchParams] = useSearchParams();
  const { setTokens } = useAuth();
  const navigate = useNavigate();
  const exchanged = useRef(false);

  useEffect(() => {
    if (exchanged.current) return;
    exchanged.current = true;

    const code = searchParams.get("code");
    if (!code) {
      navigate("/login", { replace: true });
      return;
    }

    exchangeCodeForTokens(code)
      .then((tokens) => {
        setTokens(tokens);
        navigate("/", { replace: true });
      })
      .catch(() => navigate("/login", { replace: true }));
  }, [navigate, searchParams, setTokens]);

  return <div>Signing you in...</div>;
}
