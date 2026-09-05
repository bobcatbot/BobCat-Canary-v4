import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/footer";
import { ImageStyle } from "@/components/site/image-style";

export const metadata: Metadata = { title: "Plugin - Moderation | BobCat Bot" };

/** Port of templates/web-plugins/utilities.html */
export default function UtilitiesPluginPage() {
  return (
    <div className="web-plugin">
      <section id="hero-plugin" className="d-flex align-items-center">
        <div className="container d-flex flex-column align-items-center justify-content-center">
          <h1>All the tools you need in a single bot</h1>
          <h2>
            Sometimes all you need is a small &amp; handy utility for your server.
            <br />
            BobCat got it all - From Embed messages to fun commands
          </h2>
        </div>
      </section>

      <main id="main">
        <section id="appearance" className="">
          <div className="container">
            <div className="section-title">
              <h2>Customize the looks of BobCat in your server</h2>
              <p>
                Find a way make your discord server your own! were you can change
                the color of BobCat messages,
                <br />
                How cool is that? head over to the dashboard and give it a go.
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

        <section id="cmds" className="" style={{ padding: "60px 0px 0px" }}>
          <div className="container">
            <div className="section-title">
              <h2>Useful Commands At Hand</h2>
              <p>Equip Your Server With Some Useful And Powerful Commands</p>
            </div>
          </div>
        </section>

        <div id="content-desktop">
          <section id="features" className="features" style={{ padding: "5px 0px" }}>
            <div className="container">
              <div className="row content">
                <div
                  className="col-md-6 pt-5 order-1 order-md-1 order-lg-1 aos-init aos-animate"
                  data-aos="fade-right"
                >
                  <h3>Help Command</h3>
                  <p>
                    Lost in commands? The /help command will help you out and
                    list all BobCats commands.
                  </p>
                </div>
                <div className="col-md-5 order-md-2">
                  <img
                    src="/legacy/img/features/1.png"
                    className="img-fluid"
                    alt=""
                  />
                </div>
              </div>
            </div>
          </section>
        </div>
        <div id="content-mobile">
          <section
            id="features"
            className="features"
            style={{ padding: "5px 0px 60px" }}
          >
            <div className="container">
              <div
                id="carouselExampleCaptions"
                className="carousel slide"
                data-bs-ride="false"
              >
                <div className="carousel-indicators">
                  <button
                    type="button"
                    data-bs-target="#carouselExampleCaptions"
                    data-bs-slide-to="0"
                    className="active"
                    aria-current="true"
                    aria-label="Slide 1"
                  />
                </div>
                <div className="carousel-inner">
                  <div className="carousel-item active">
                    <img
                      src="/legacy/img/features/1.png"
                      className="d-block w-100"
                      alt="fake image"
                    />
                    <div className="carousel-caption position-static">
                      <h3>Help Command</h3>
                      <p>
                        Lost in commands? The /help command will help you out and
                        list all BobCats commands.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <section id="embeds" className="">
          <div className="container">
            <div className="section-title">
              <h2>Send Rich Embeds In Your Discord Server</h2>
              <p>Create, design, edit &amp; send embed messages in your server.</p>
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
      </main>

      <SiteFooter />

      <ImageStyle />
    </div>
  );
}
