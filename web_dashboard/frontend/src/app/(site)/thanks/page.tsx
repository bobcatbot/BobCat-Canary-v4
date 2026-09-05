import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/footer";

export const metadata: Metadata = { title: "Thanks | BobCat Bot" };

const headingStyle = {
  fontWeight: "bold",
  textTransform: "uppercase" as const,
  marginBottom: "20px",
  paddingBottom: 0,
  color: "#FFFFFF",
};

/** Port of templates/thanks.html */
export default function ThanksPage() {
  return (
    <>
      <section id="services" className="info-cards pt-0">
        <div className="container">
          <div
            className=""
            style={{
              paddingTop: "90px",
              textAlign: "center",
              paddingBottom: "30px",
            }}
          >
            <h2 style={{ ...headingStyle, fontSize: "2.25rem" }}>
              Thanks for adding
            </h2>

            <h1 style={{ ...headingStyle, fontSize: "80px" }}>BobCat</h1>

            <h4 style={{ ...headingStyle, fontSize: "1.125rem" }}>
              To help you get started using our bot you can take a look around
              this website where most aspects of the bot are documented.
            </h4>
          </div>

          <div className="row">
            <div className="col-lg-4 col-md-6">
              <a href="https://www.docs.bobcatbot.xyz/">
                <div className="icon-box">
                  <div className="icon">
                    <span className="material-icons" style={{ fontSize: "64px" }}>
                      article
                    </span>
                  </div>
                  <h4 className="title">Commands</h4>
                  <p className="description">
                    See all of the commands BobCat has to offer your server!
                  </p>
                </div>
              </a>
            </div>

            <div className="col-lg-4 col-md-6">
              <a href="https://www.docs.bobcatbot.xyz/home/faq">
                <div className="icon-box">
                  <div className="icon">
                    <span className="material-icons" style={{ fontSize: "64px" }}>
                      help
                    </span>
                  </div>
                  <h4 className="title">FAQ</h4>
                  <p className="description">
                    Have some questions? See if we&apos;ve already answered it on
                    this page!
                  </p>
                </div>
              </a>
            </div>

            <div className="col-lg-4 col-md-6">
              <a href="https://www.help.bobcatbot.xyz/">
                <div className="icon-box">
                  <div className="icon">
                    <span className="material-icons" style={{ fontSize: "64px" }}>
                      help_center
                    </span>
                  </div>
                  <h4 className="title">Help Desk</h4>
                  <p className="description">
                    See all of the commands BobCat has to offer your server!
                  </p>
                </div>
              </a>
            </div>

            <div className="col-lg-4 col-md-6">
              <a href="https://discord.com/invite/T7zE4x4xbT">
                <div className="icon-box">
                  <div className="icon">
                    <span className="material-icons" style={{ fontSize: "64px" }}>
                      support_agent
                    </span>
                  </div>
                  <h4 className="title">Support</h4>
                  <p className="description">
                    FAQ page not enough to help? Head over to our support server!
                  </p>
                </div>
              </a>
            </div>

            <div className="col-lg-4 col-md-6">
              <a href="https://discord.com/invite/T7zE4x4xbT">
                <div className="icon-box">
                  <div className="icon">
                    <span className="material-icons" style={{ fontSize: "64px" }}>
                      people
                    </span>
                  </div>
                  <h4 className="title">Community</h4>
                  <p className="description">
                    FAQ page not enough to help? Head over to our support server!
                  </p>
                </div>
              </a>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />

      <style>{`
.info-cards .icon-box {
  padding: 30px;
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  margin: 0 10px 40px 10px;
  background: #424547;
  box-shadow: 0 10px 29px 0 rgb(68 88 144 / 10%);
  transition: all 0.3s ease-in-out;
}

.info-cards .icon {
  position: absolute;
  top: calc(50% - 30px);
}

.info-cards .title {
  color: #FFFFFF;
  margin-left: 90px;
  font-weight: 700;
  margin-bottom: 15px;
  font-size: 17px;
}

.info-cards .description {
  color: #FFFFFF;
  font-size: 14px;
  margin-left: 90px;
  line-height: 24px;
  margin-bottom: 0;
}
`}</style>
    </>
  );
}
