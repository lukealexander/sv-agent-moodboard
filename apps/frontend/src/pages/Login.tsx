import { useEffect } from "react";
import { useAuth } from "../auth/AuthContext";
import { redirectToLogin } from "../auth/cognito";
import styles from "./Login.module.css";

export function Login() {
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      window.location.replace("/");
    }
  }, [isAuthenticated, isLoading]);

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.heading}>Sign in</h1>
        <button className={styles.primary} onClick={() => void redirectToLogin()}>
          Continue with Cognito
        </button>
      </div>
    </div>
  );
}
