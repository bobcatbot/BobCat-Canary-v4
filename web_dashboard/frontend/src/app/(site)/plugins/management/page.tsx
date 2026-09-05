import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/footer";

export const metadata: Metadata = { title: "Plugin - Moderation | BobCat Bot" };

/** Port of templates/web-plugins/management.html */
export default function ManagementPluginPage() {
  return (
    <div className="web-plugin">
      <section id="hero-plugin" className="d-flex align-items-center">
        <div className="container d-flex flex-column align-items-center justify-content-center">
          <h1>The Best Moderation Bot For Discord</h1>
          <h3>BobCat Can Take Care Of Everthing By Doing All The Work For You.</h3>
        </div>
      </section>

      <main id="main">
        <section id="features" className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5">
                <img src="/legacy/img/features/5.png" className="img-fluid" alt="" />
              </div>

              <div className="col-md-7 pt-4">
                <h3>
                  Keep Your Server(s) Safe &amp; Clean With Our High-Quality
                  Auto-Mod System.
                </h3>
                <p className="fst-italic" style={{ color: "#939399" }}>
                  No One Likes Their Server(s) Spammed Or Destroyed By Trolles?
                  Well You Don&rsquo;t Have To Worry Anymore!
                  <br />
                  Setup Auto-Mod For Your Server(s) Today! And Let BobCat Do Is
                  Work By Protecting Your Server(s) Even When You&rsquo;re
                  Sleeping.
                </p>

                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-check" /> You Will Be 99% Less Worried
                    Leaving Your Server(s) Alone Over Night Or When Your Away.
                  </li>
                  <li>
                    <i className="bi bi-check" /> BobCat Is always Actively
                    Scaning Your Channels 24/7.
                  </li>
                  <li>
                    <i className="bi bi-check" /> By Setting BobCats Role To The
                    Highest Level, You Are Guaranteed Safer Server&apos;s All Day
                    Long.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5 order-1 order-md-2">
                <img src="/legacy/img/features/6.png" className="img-fluid" alt="" />
              </div>
              <div className="col-md-7 pt-5 order-2 order-md-1">
                <h3>
                  Fight Back With Auto Mod Like Filters And Remove Unwanted People
                  From Your Server(s).
                </h3>
                <p style={{ color: "#939399" }} className="fst-italic">
                  Protect Your Server(s) From Unwanted Or Bad Links Within
                  Channels. Plus Get more Out Of BobCat&apos;s Auto Mod Filters
                  Within Our{" "}
                  <a href="https://dashboard.bobcatbot.xyz" target="_blank">
                    Dashboard
                  </a>
                  .
                </p>
                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-star-fill" /> Block Out Unwanted Links,
                    Images or Words Within Your Server(s)
                    <br />
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;And Feel Fresh All
                    round Your Channels!
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> Sit Back And Relex As BobCat
                    Seeks Though All Channels Spotting For Unwated Material(s).
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> Allow BobCat To Timeout
                    Members Up to &quot;1 Week&quot; After Sending Unwanted
                    Material Within Your
                    <br />
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Server(s).
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5">
                <img src="/legacy/img/features/7.png" className="img-fluid" alt="" />
              </div>
              <div className="col-md-7 pt-5">
                <h3>
                  Keep A Track Of Important Events Happening Around Your
                  Server(s).
                </h3>
                <p style={{ color: "#939399" }} className="fst-italic">
                  Choose A Private Channel Where BobCat Will Notify Mod&apos;s
                  Whether Someone Updates / Deletes Messages In Any Channel Around
                  Your Server(s).
                </p>
                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-check" /> BobCat Will Notify All Mods In
                    The Server(s).
                  </li>
                  <li>
                    <i className="bi bi-check" /> Keeps All Log Message&apos;s
                    Separate And Hidden From Members.
                  </li>
                  <li>
                    <i className="bi bi-check" /> When Somthing Within your
                    Server(s) Changes BobCat Will Know.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5 order-1 order-md-2">
                <img src="/legacy/img/features/8.png" className="img-fluid" alt="" />
              </div>
              <div className="col-md-7 pt-5 order-2 order-md-1">
                <h3>Boost Your Moderator&apos;s Productivity.</h3>
                <p style={{ color: "#939399" }} className="fst-italic">
                  Give Your Moderator&apos;s The Right Tool&apos;s To Keep Your
                  Server(s) Safe With BobCat&apos;s Mod Commands.
                  <br />
                  All Mod&apos;s Have Access To Over 20+ Pre-Made Commands To
                  Control Your Server(s).
                </p>
                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-star-fill" /> Help Your Server(s) Be At
                    It&apos;s Best With Mod Commands Such As Ban, Mute, Warn Plus
                    Lot&apos;s More
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You Can{" "}
                    <a href="https://docs.bobcatbot.xyz/moderation/" target="_blank">
                      Discover.
                    </a>
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> Allow Mod&apos;s To Annouce
                    Messages With BobCat With A Simple Command.
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> Get To Know Your Limits By
                    Hosting Polls, Echo Messages, Create Emojis.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section id="welcome" className="">
          <div className="container">
            <div className="section-title">
              <h2>Welcome your new members</h2>
              <p>
                Take avantage of the welcome message to inform new members about
                your server rules, topic, or ongoing events.
                <br />
                You can design your own welcome messages or keep it simple all
                within our dashboard.
              </p>
            </div>
            <div className="d-flex justify-content-center">
              <img
                src="/legacy/img/features/1.png"
                className="img-fluid image"
                alt=""
              />
            </div>
          </div>
          <style>{`
        .image {
          width: 50%;
        }
        @media (max-width: 992px) {
          .image {
            width: 100%;
          }
        }
      `}</style>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
