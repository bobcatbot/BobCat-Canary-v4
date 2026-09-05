/** Port of templates/components/footer.html */
export function SiteFooter() {
  return (
    <footer id="footer">
      <div className="footer-top">
        <div className="container">
          <div className="row">
            <div className="col-lg-3 col-md-6 footer-contact">
              <h3>BobCat Inc.</h3>
              <p>
                A Team Of Talented Designers <br />
                Taking Your Discord Server
                <br />
                To The Next Level.
                <br />
                <br />
                <strong>Dev Email:</strong> dev@bobcatbot.xyz
                <br />
                <strong>Support Email:</strong> support@bobcatbot.xyz
                <br />
              </p>
            </div>

            <div className="col-lg-2 col-md-6 footer-links">
              <h4>Our Website</h4>
              <ul>
                <li>
                  <i className="bx bx-chevron-right" /> <a href="#hero">Home</a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="#about">About us</a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="https://shop.bobcatbot.xyz/" target="_blank">
                    Our Shop
                  </a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" /> <a href="#team">Our Team</a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" /> <a href="#faq">Faq&apos;s</a>
                </li>
              </ul>
            </div>

            <div className="col-lg-3 col-md-6 footer-links">
              <h4>Useful Links</h4>
              <ul>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="https://status.bobcatbot.xyz/" target="_blank">
                    Status
                  </a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="https://docs.bobcatbot.xyz" target="_blank">
                    BobCat Doc&apos;s
                  </a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="https://discord.gg/xNnaVrEwke" target="_blank">
                    Support Server
                  </a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="/contact-us" target="_blank">
                    Contact Us
                  </a>
                </li>
              </ul>
            </div>

            <div className="col-lg-2 col-md-6 footer-links">
              <h4>Comapany</h4>
              <ul>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="https://careers.bobcatbot.xyz/" target="_blank">
                    Careers
                  </a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" /> <a href="/rules">Bot Rules</a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a href="/terms">Terms of service</a>
                </li>
                <li>
                  <i className="bx bx-chevron-right" />{" "}
                  <a style={{ color: "#939399" }}>Privacy policy</a>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="container d-md-flex py-4">
        <div className="me-md-auto text-center text-md-start">
          <div className="copyright">
            &copy; Copyright{" "}
            <strong>
              <span>BobCat Inc.</span>
            </strong>{" "}
            All Rights Reserved
          </div>
        </div>
      </div>
    </footer>
  );
}
