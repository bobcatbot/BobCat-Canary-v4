import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/footer";
import { ImageStyle } from "@/components/site/image-style";

export const metadata: Metadata = { title: "Plugin - Moderation | BobCat Bot" };

/** Port of templates/web-plugins/engagement-and-fun.html */
export default function EngagementPluginPage() {
  return (
    <div className="web-plugin">
      <section id="hero-plugin" className="d-flex align-items-center">
        <div className="container d-flex flex-column align-items-center justify-content-center">
          <h1>
            Things are better <br /> with your friends
          </h1>
        </div>
      </section>

      <main id="main">
        <section id="levelling">
          <div className="container">
            <div className="section-title">
              <h2>Boost your server engagement with Leveling</h2>
              <p>
                Reward your members with XP points and keep track of the most
                active members on your customizable leaderboard.
              </p>
            </div>
            <div className="d-flex justify-content-center">
              <img
                src="/legacy/img/features/2.png"
                className="img-fluid image"
                alt=""
              />
            </div>
          </div>
        </section>

        <section id="welcome-members">
          <div className="container">
            <div className="section-title">
              <h2>Gamify your Discord server with BobCat&apos;s Economy </h2>
              <p>
                Create your own currency and items at the shop. Let your users
                work for some hard earned cash
              </p>
            </div>
            <div className="d-flex justify-content-center">
              <img
                src="/legacy/img/features/3.png"
                className="img-fluid image"
                alt=""
              />
            </div>
          </div>
        </section>

        <section id="engagement">
          <div className="container">
            <div className="section-title">
              <h2>User Engagement</h2>
              <p>
                Use our starboard system to show off the funniest jokes of all
                time!
              </p>
            </div>
            <div className="d-flex justify-content-center">
              <img
                src="/legacy/img/features/4.png"
                className="img-fluid image"
                alt=""
              />
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />

      <ImageStyle />
    </div>
  );
}
