import { LegacyStyles } from "@/components/site/legacy-styles";

/**
 * Shared body of templates/error/404.html and templates/error/NoAccess.html
 * (identical except the text). The inline <style> is verbatim from those
 * templates; it fully determines the look, so we only need Bootstrap's base
 * `.btn` + the Balsamiq font from LegacyStyles rather than the whole
 * dash-links.html vendor stack.
 */
export function ErrorCard({
  heading,
  message,
  href = "/dashboard",
  cta = "Back to home",
}: {
  heading: string;
  message: string;
  href?: string;
  cta?: string;
}) {
  return (
    <>
      <LegacyStyles />
      <main className="error">
        <div className="e-card">
          <h1>{heading}</h1>
          <h2>{message}</h2>
          <a className="btn" href={href}>
            {cta}
          </a>
        </div>
      </main>

      <style>{`
body {
  color: #fff;
  background: #272934;
}
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  height: 100dvh;
}
.error .e-card {
  width: max-content;
  height: max-content;
  padding: 36px;
  color: #fff;
  background: #1f2129;
  border-radius: 25px;
}
.error .e-card h1 {
  font-size: 130px;
  font-weight: 700;
  margin-bottom: 0;
}
.error .e-card h2 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 30px;
}
.error .e-card .btn {
  background: #51678f;
  color: #fff;
  padding: 8px 30px;
}
.error .e-card .btn:hover {
  background: #3e4f6f;
}
@media (min-width: 992px) {
  .error-404 img {
    max-width: 50%;
  }
}
`}</style>
    </>
  );
}
