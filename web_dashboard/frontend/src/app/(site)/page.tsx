import type { Metadata } from "next";
import { INVITE_URL } from "@/lib/discord";
import { SiteFooter } from "@/components/site/footer";

export const metadata: Metadata = { title: "Home | BobCat Bot" };

/** Port of templates/index.html */
export default function HomePage() {
  return (
    <>
      {/* ======= Hero Section ======= */}
      <section id="hero" className="d-flex align-items-center">
        <div
          className="container d-flex flex-column align-items-center justify-content-center"
          data-aos="fade-up"
        >
          <img
            id="hero-image"
            src="/legacy/img/bobcat.png"
            className="img-fluid hero-img"
            alt=""
            data-aos="zoom-in"
            data-aos-delay="150"
          />
          <h1>Build The Best Discord Server With BobCat!</h1>
          <h2>
            Configure Moderation, Leveling, Welcoming <br /> Plus So Much More
            With A Easy-To-Use Dashboard!
          </h2>
          <div className="d-flex">
            <a
              style={{ cursor: "pointer" }}
              className="btn-get-started"
              target="_blank"
              href={INVITE_URL}
            >
              Add to Discord
            </a>
            <a className="btn-get-started" href="#about">
              Learn More
            </a>
          </div>
        </div>
      </section>

      <main id="main">
        {/* ======= About Section ======= */}
        <section id="about" className="about">
          <div className="container">
            <div className="row no-gutters">
              <div className="content col-xl-5 d-flex align-items-stretch">
                <div className="content">
                  <h3>
                    What&apos;s Up With BobCat?
                    <br /> Learn Everything You Need To Know About Him.
                  </h3>
                  <p>
                    BobCat Is More Than Just A Discord Bot, He Is Like A Family
                    Member To Each Server He Is In! BobCat Bring&apos;s Happiness
                    Not Just Servers, But Also your Face Because You Know You Are
                    Safe 24/7!
                  </p>
                  <a style={{ cursor: "pointer" }} className="about-btn">
                    <i>#</i> Team BobCat
                  </a>
                </div>
              </div>

              <div className="col-xl-7 d-flex align-items-stretch">
                <div className="icon-boxes d-flex flex-column justify-content-center">
                  <div className="row">
                    <div className="col-md-6 icon-box">
                      <i className="bi bi-cpu-fill" />
                      <h4>Features.</h4>
                      <p>
                        We Have A &apos;Auto Hacker&apos; Detecter Within
                        BobCat&apos;s Code Which Alerts You When A Problem
                        Apper&apos;s In Your Server(s).
                      </p>
                    </div>
                    <div className="col-md-6 icon-box">
                      <i className="bi bi-check-circle-fill" />
                      <h4>Online 24/7.</h4>
                      <p>
                        Our Goal Is To Keep BobCat Online As Long As Possible, To
                        Keeps Every Server Happy.
                      </p>
                      <p>
                        We keep BobCat Updated To Our Best, To Fit In For
                        Everyones Needs / Accessibility.
                      </p>
                    </div>
                    <div className="col-md-6 icon-box">
                      <i className="bi bi-chat-square-dots-fill" />
                      <h4>Dashboard.</h4>
                      <p>
                        Connect With Our Dashboard And Enhance Your Server(s) To
                        It&apos;s Max Potential!
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ======= Shop Section ======= */}
        <section id="shop" className="call-to-action">
          <div className="container">
            <div className="row justify-content-center">
              <div className="col-lg-8 text-center">
                <h1 style={{ color: "white" }}>
                  <b>NEW</b>
                </h1>
                <h3>Shop With BobCat!</h3>
                <p>
                  Discover All Of Products Based Around BobCat, Feel Free To Take
                  Look.
                  <br />
                  <br />
                  <img src="/legacy/img/english.png" alt="" />
                  UK SHIPPING ONLY
                  <img src="/legacy/img/english.png" alt="" />
                </p>
                <a
                  className="button"
                  href="https://shop.bobcatbot.xyz/"
                  target="_blank"
                >
                  Browse products
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* ======= Welcome Section ======= */}
        <section className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5">
                <img
                  src="/legacy/img/features/1.png"
                  className="img-fluid"
                  alt=""
                />
              </div>

              <div className="col-md-7 pt-4">
                <h3>Say Hello To New Users On Your Discord Server!</h3>
                <p className="fst-italic" style={{ color: "#939399" }}>
                  Take Avantage Of The Welcome Message To Inform New Members About
                  Your Server Rules, Topic, Or Ongoing Events. You Can Design Your
                  Own Welcome Messages Or Keep It Simple All Within Our Dashboard.
                </p>

                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-check" /> Enable / Disable The welcome
                    Feature In The Dashbaord.
                  </li>
                  <li>
                    <i className="bi bi-check" /> Make Everything Neat, By Telling
                    BobCat Witch Channel Is For New-Comers.
                  </li>
                  <li>
                    <i className="bi bi-check" /> Customise Your Message From
                    BobCat For When A New Member Joins.
                  </li>

                  <a className="learn-more" href="/plugins/management#welcome">
                    More About Welcoming
                  </a>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ======= Leveling Section ======= */}
        <section className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5 order-1 order-md-2">
                <img
                  src="/legacy/img/features/2.png"
                  className="img-fluid"
                  alt=""
                />
              </div>
              <div className="col-md-7 pt-5 order-2 order-md-1">
                <h3>Level&apos;s and XP In Your Server(s).</h3>
                <p style={{ color: "#939399" }} className="fst-italic">
                  Use Our Leveling System To Identify And Reward Your Most Active
                  Members Of Your Server(s) / Community. Let Your Members Show Off
                  A Cool Rank Card And Compete For The Mighty First Place Spot Of
                  Your Leaderboard!
                </p>
                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-star-fill" /> Have The Highest Rank /
                    Level / Point&apos;s On Your Server(s).
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> Compete Against Other
                    Members, And Become The Ultimate &apos;Level Boss&apos; Of
                    The Server.
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> With Our Leveling System You
                    Have The Power To Customise The Leveling / Rank Cards.
                  </li>

                  <a
                    className="learn-more"
                    href="/plugins/engagement-and-fun#levelling"
                  >
                    More about levelling
                  </a>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ======= Customize Section ======= */}
        <section className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5">
                <img
                  src="/legacy/img/features/3.png"
                  className="img-fluid"
                  alt=""
                />
              </div>
              <div className="col-md-7 pt-5">
                <h3>Customize the Look&apos;s Of BobCat In Your Server(s).</h3>
                <p style={{ color: "#939399" }} className="fst-italic">
                  Find A Way Make Your Discord Server(s) Your Own! Were You Can
                  Change The Color Of BobCat, How Cool Is That? Head Over To The
                  Dashboard And Give It A Go.
                </p>
                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-check" /> Personilsed To Your Own Ability.
                  </li>
                  <li>
                    <i className="bi bi-check" /> Uniqe To Every Other Server(s)
                    Out There.
                  </li>
                  <li>
                    <i className="bi bi-check" /> Fits In With Your Color Scheme
                    Throughout Your Whole Server(s).
                  </li>

                  <a className="learn-more" href="/plugins/utilities#appearance">
                    More about appearance
                  </a>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ======= User Engagement Section ======= */}
        <section className="features">
          <div className="container">
            <div className="row content">
              <div className="col-md-5 order-1 order-md-2">
                <img
                  src="/legacy/img/features/4.png"
                  className="img-fluid"
                  alt=""
                />
              </div>
              <div className="col-md-7 pt-5 order-2 order-md-1">
                <h3>User Engagement With Server&apos;s (Starboard).</h3>
                <p style={{ color: "#939399" }} className="fst-italic">
                  Use Our Starboard System To Show Off The Funniest Joke&apos;s Of
                  All Time!
                </p>
                <ul style={{ color: "#939399" }}>
                  <li>
                    <i className="bi bi-star-fill" /> Start With Laughs &amp;
                    Gag&apos;s At All Your Funny jokes With Your Friend&apos;s.
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> Have A Designated Channel
                    For All Your Fun.
                  </li>
                  <li>
                    <i className="bi bi-star-fill" /> Be A Master At Jokes With
                    BobCat By Unleashing All The Cracking, Funny, Amazing, Cool
                    Jokes.
                  </li>

                  <a
                    className="learn-more"
                    href="/plugins/engagement-and-fun#engagement"
                  >
                    More about engagemnt
                  </a>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ======= Services Section ======= */}
        <section id="plugins" className="services">
          <div className="container">
            <div className="section-title">
              <h2>Plugins</h2>
              <p style={{ color: "#939399" }}>
                BobCats Plug-ins Are Awsome! From Easy-To-Use Interaction&apos;s
                Within The Dashboard &amp; Discord It&apos;s Self.
              </p>
            </div>

            <div className="row d-flex justify-content-center">
              <div className="col-md-6 col-lg-3 d-flex align-items-stretch mb-5 mb-lg-0">
                <div className="icon-box">
                  <div className="icon">
                    <i className="bi bi-wrench-adjustable" />
                    <br />
                    <br />
                  </div>
                  <h4 className="title">Moderation &amp; Management</h4>
                  <p className="description">
                    BobCat can take care of everything From welcoming new users to
                    auto-kicking members out of your server.
                  </p>
                  <a className="learn-more-btn" href="/plugins/management">
                    Learn more
                  </a>
                </div>
              </div>

              <div className="col-md-6 col-lg-3 d-flex align-items-stretch mb-5 mb-lg-0">
                <div className="icon-box">
                  <div className="icon">
                    <i className="bi bi-clipboard-check-fill" />
                    <br />
                    <br />
                  </div>
                  <h4 className="title">
                    <a href="">BobCat Utilities</a>
                  </h4>
                  <p className="description">
                    Sometimes all you need is a small &amp; handy utility for your
                    server.
                  </p>
                  <a className="learn-more-btn" href="/plugins/utilities">
                    Learn more
                  </a>
                </div>
              </div>

              <div className="col-md-6 col-lg-3 d-flex align-items-stretch mb-5 mb-lg-0">
                <div className="icon-box">
                  <div className="icon">
                    <i className="bi bi-balloon-fill" />
                    <br />
                    <br />
                  </div>
                  <h4 className="title">
                    <a href="">Engagement &amp; Fun</a>
                  </h4>
                  <p className="description">
                    Things are always better with your friends.
                  </p>
                  <a
                    className="learn-more-btn"
                    href="/plugins/engagement-and-fun"
                  >
                    Learn more
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ======= Team Section ======= */}
        <section id="team" className="team">
          <div className="container">
            <div className="section-title">
              <h2>Our Team</h2>
              <p style={{ color: "#939399" }}>
                Meet Our Team Who Have There Own Special Skill&apos;s Within
                Working With BobCat.
              </p>
            </div>

            <div id="content-desktop">
              <div className="row" style={{ justifyContent: "center" }}>
                <div className="col-xl-3 col-lg-4 col-md-6">
                  <div className="member">
                    <img
                      src="/legacy/img/team/team-1.png"
                      className="img-fluid"
                      alt=""
                    />
                    <div className="member-info">
                      <div className="member-info-content">
                        <h4>BananaBobs2004</h4>
                        <span>CEO / Founder / Core Web Developer</span>
                      </div>
                      <div className="social">
                        <a
                          href="https://solo.to/bobbyjackstott"
                          target="_blank"
                        >
                          <i className="bi bi-discord" />
                        </a>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="col-xl-3 col-lg-4 col-md-6">
                  <div className="member">
                    <img
                      src="/legacy/img/team/team-2.png"
                      className="img-fluid"
                      alt=""
                    />
                    <div className="member-info">
                      <div className="member-info-content">
                        <h4>DinoTech</h4>
                        <span>CO-CEO / Core Developer</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div id="content-mobile">
              <div
                id="carouselExampleIndicators"
                className="carousel slide"
                data-bs-ride="true"
              >
                <div className="carousel-indicators">
                  <button
                    type="button"
                    data-bs-target="#carouselExampleIndicators"
                    data-bs-slide-to="0"
                    className="active"
                    aria-current="true"
                    aria-label="Slide 1"
                  />
                  <button
                    type="button"
                    data-bs-target="#carouselExampleIndicators"
                    data-bs-slide-to="1"
                    aria-label="Slide 2"
                  />
                </div>

                <div className="carousel-inner">
                  <div className="member carousel-item active">
                    <img
                      src="/legacy/img/team/team-1.png"
                      className="d-block w-100"
                      alt=""
                    />
                    <div className="carousel-caption position-static">
                      <h5>BananaBobs2004</h5>
                      <p>CEO / Founder / Lead Web Developer</p>
                    </div>
                  </div>
                  <div className="member carousel-item">
                    <img
                      src="/legacy/img/team/team-2.png"
                      className="d-block w-100"
                      alt=""
                    />
                    <div className="carousel-caption position-static">
                      <h5>DinoTech</h5>
                      <p>CO-CEO / Lead Bot Developer</p>
                    </div>
                  </div>
                </div>
                <button
                  className="carousel-control-prev"
                  type="button"
                  data-bs-target="#carouselExampleIndicators"
                  data-bs-slide="prev"
                >
                  <span
                    className="carousel-control-prev-icon"
                    aria-hidden="true"
                  />
                  <span className="visually-hidden">Previous</span>
                </button>
                <button
                  className="carousel-control-next"
                  type="button"
                  data-bs-target="#carouselExampleIndicators"
                  data-bs-slide="next"
                >
                  <span
                    className="carousel-control-next-icon"
                    aria-hidden="true"
                  />
                  <span className="visually-hidden">Next</span>
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </>
  );
}
