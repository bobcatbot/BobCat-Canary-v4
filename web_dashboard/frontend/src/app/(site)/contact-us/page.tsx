import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/footer";

export const metadata: Metadata = { title: "Contact Us | BobCat Bot" };

/** Port of templates/contact-us.html */
export default function ContactUsPage() {
  return (
    <>
      <section className="page-header d-flex align-items-center">
        <div
          className="container d-flex flex-column align-items-center justify-content-center"
          data-aos="fade-up"
        >
          <h1>Contact Us</h1>
        </div>
      </section>

      <main>
        <section id="about" className="">
          <div className="container">
            <div className="content d-flex align-items-stretch" data-aos="fade-right">
              <div className="content">
                <p>
                  Contact our BobCat Support Team any time via email at{" "}
                  <a href="mailto: support@bobcatbot.xyz">
                    support@bobcatbot.xyz
                  </a>
                </p>
                <p>
                  For order inquiries, please contact us from the email address
                  you placed your order with and include your order number for
                  faster service.
                </p>
                <p>We typically reply in 1-4 business days!</p>
                <p>Thank you for your patience ♥️</p>
              </div>
            </div>
          </div>
        </section>

        <section id="socilas" className="">
          <div className="container">
            <div className="section-title">
              <h2>Social media</h2>
            </div>

            <div className="content d-flex align-items-stretch" data-aos="fade-right">
              <div className="content">
                <a href="https://discord.gg/xNnaVrEwke" className="btn btn-secondary">
                  <i className="bi bi-discord" />
                  Discord
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />

      <style>{`
  .page-header {
    padding: 120px 0px 70px 0px;
    position: relative;
    width: 100%;
    height: 100%;
    color: #ffffff;
    background: #36393F;
    border-bottom: 2px solid #36393F;
    text-align: center;
  }
`}</style>
    </>
  );
}
