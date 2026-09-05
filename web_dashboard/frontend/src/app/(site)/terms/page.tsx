import type { Metadata } from "next";
import { SiteFooter } from "@/components/site/footer";

export const metadata: Metadata = { title: "Terms | BobCat Bot" };

/** Port of templates/terms.html */
export default function TermsPage() {
  return (
    <>
      <section className="page-header d-flex align-items-center">
        <div
          className="container d-flex flex-column align-items-center justify-content-center"
          data-aos="fade-up"
        >
          <h1>TERMS OF SERVICE</h1>
          <h6>Last updated: October 4th, 2022</h6>
        </div>
      </section>

      <main>
        <section id="about" className="about">
          <div className="container">
            <div>
              Please read these Terms of Service (&quot;Terms&quot;, &quot;Terms
              of Service&quot;) carefully before using the{" "}
              <a href="https://www.bobcatbot.xyz">https://www.bobcatbot.xyz</a>{" "}
              website (the &quot;Service&quot;) operated by BobCat Inc (&quot;
              <b>Company,</b>&quot; &quot;<b>we,</b>&quot; &quot;<b>us,</b>&quot;
              or &quot;<b>our</b>&quot;).
            </div>

            <div style={{ marginTop: "4px" }}>
              Your access to and use of the Service is conditioned upon your
              acceptance of and compliance with these Terms. These Terms apply to
              all visitors, users and others who wish to access or use the
              Service.
            </div>

            <div style={{ marginTop: "4px" }}>
              By accessing or using the Service you agree to be bound by these
              Terms. If you disagree with any part of the terms then you do not
              have permission to access the Service.
            </div>

            <div style={{ marginTop: "4px" }}>
              <b>How do we keep your information safe?</b> We have organizational
              and technical processes and procedures in place to protect your
              personal information. However, no electronic transmission over the
              internet or information storage technology can be guaranteed to be
              100% secure, so we cannot promise or guarantee that hackers,
              cybercriminals, or other unauthorized third parties will not be
              able to defeat our security and improperly collect, access, steal,
              or modify your information.
            </div>

            <div>
              <h4 style={{ marginTop: "15px", fontWeight: 700 }}>Information</h4>
              <div style={{ marginTop: "4px" }}>
                Personal information you disclose to us
              </div>
              <div style={{ marginTop: "4px" }}>
                <b>In Short:</b> We collect personal information that you provide
                to us.
              </div>
              <div style={{ marginTop: "4px" }}>
                We collect personal information that you voluntarily provide to us
                when you express an interest in obtaining information about us or
                our products and Services, when you participate in activities on
                the Services, or otherwise when you contact us.
              </div>
              <div style={{ marginTop: "4px" }}>
                <b>Personal Information Provided by You.</b> The personal
                information that we collect depends on the context of your
                interactions with us and the Services, the choices you make, and
                the products and features you use. The personal information we
                collect may include the following:
                <ul>
                  <li>names</li>
                  <li>email addresses</li>
                  <li>usernames</li>
                  <li>passwords</li>
                  <li>contact or authentication data</li>
                </ul>
              </div>
              <div style={{ marginTop: "4px" }}>
                We <b>do not</b> process any sensitive information. Unless the
                data will be harming us or the user
              </div>
              <div style={{ marginTop: "4px" }}>
                All personal information that you provide to us must be true,
                complete, and accurate, and you must notify us of any changes to
                such personal information.
              </div>
            </div>

            <div>
              <h4 style={{ marginTop: "15px", fontWeight: 700 }}>
                How long do we keep your information?
              </h4>
              <div style={{ marginTop: "4px" }}>
                <b>In Short:</b> We keep your information for as long as necessary
                to fulfill the purposes outlined in this privacy notice unless
                otherwise required by law.
              </div>
              <div style={{ marginTop: "4px" }}>
                We will only keep your personal information for as long as it is
                necessary for the purposes set out in this privacy notice, unless
                a longer retention period is required or permitted by law (such as
                tax, accounting, or other legal requirements). No purpose in this
                notice will require us keeping your personal information for
                longer than 1 year.
              </div>
              <div style={{ marginTop: "4px" }}>
                When we have no ongoing legitimate business need to process your
                personal information, we will either delete or anonymize such
                information, or, if this is not possible (for example, because
                your personal information has been stored in backup archives),
                then we will securely store your personal information and isolate
                it from any further processing until deletion is possible.
              </div>
            </div>

            <div>
              <h4 style={{ marginTop: "15px", fontWeight: 700 }}>
                How do we keep your information safe?
              </h4>
              <div style={{ marginTop: "4px" }}>
                <b>In Short:</b> We aim to protect your personal information
                through a system of organizational and technical security
                measures.
              </div>
              <div style={{ marginTop: "4px" }}>
                We have implemented appropriate and reasonable technical and
                organizational security measures designed to protect the security
                of any personal information we process. However, despite our
                safeguards and efforts to secure your information, no electronic
                transmission over the Internet or information storage technology
                can be guaranteed to be 100% secure, so we cannot promise or
                guarantee that hackers, cybercriminals, or other unauthorized
                third parties will not be able to defeat our security and
                improperly collect, access, steal, or modify your information.
                Although we will do our best to protect your personal
                information, transmission of personal information to and from our
                Services is at your own risk. You should only access the Services
                within a secure environment.
              </div>
            </div>

            <div>
              <h4 style={{ marginTop: "15px", fontWeight: 700 }}>Changes</h4>
              <div style={{ marginTop: "4px" }}>
                We reserve the right, at our sole discretion, to modify or replace
                these Terms at any time. If a revision is material we will provide
                at least 30 days notice prior to any new terms taking effect. What
                constitutes a material change will be determined at our sole
                discretion.
              </div>
              <div style={{ marginTop: "4px" }}>
                By continuing to access or use our Service after any revisions
                become effective, you agree to be bound by the revised terms. If
                you do not agree to the new terms, you are no longer authorized to
                use the Service.
              </div>
            </div>
            <div>
              <h4 style={{ marginTop: "15px", fontWeight: 700 }}>Contact us</h4>
              <div style={{ marginTop: "4px" }}>
                If you have any questions about our Terms, please contact us by
                email:{" "}
                <a href="mailto: owners@bobcatbot.xyz">owners@bobcatbot.xyz</a>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </>
  );
}
