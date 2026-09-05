/** Port of templates/components/PremiumModal.html. Opened by main.js /
 *  handlePremiumOnClick when a premium plugin is clicked without premium. */
export function PremiumModal({ guildId }: { guildId: string }) {
  return (
    <div id="PremiumModal" className="modal dark" tabIndex={-1}>
      <div className="modal-dialog modal-dialog-centered">
        <div className="modal-content">
          <div className="modal-body position-relative">
            <div
              className="position-absolute"
              style={{
                top: "var(--bs-modal-padding)",
                right: "var(--bs-modal-padding)",
              }}
            >
              <button
                type="button"
                className="btn-close"
                data-bs-dismiss="modal"
                aria-label="Close"
              />
            </div>

            <div className="d-flex flex-row main-content">
              <div className="d-none d-md-block bg-img" />

              <div className="content w-100 d-flex flex-column justify-content-center">
                <h5 className="m-0">
                  You discovered a{" "}
                  <span style={{ color: "#5865f2" }}>Premium</span> feature!
                </h5>
                <h5 className="m-0">Upgrade to unlock it.</h5>

                <ul
                  style={{
                    listStyle: "none",
                    paddingLeft: 0,
                    marginTop: "0.9rem",
                    marginBottom: "1rem",
                  }}
                >
                  <li className="d-flex align-items-center">
                    <i className="bi bi-check icon" />
                    Access to everything
                  </li>
                  <li className="d-flex align-items-center">
                    <i className="bi bi-check icon" />
                    Early access
                  </li>
                  <li className="d-flex align-items-center">
                    <i className="bi bi-check icon" />
                    Fully refundable for 7 days
                  </li>
                  <li className="d-flex align-items-center">
                    <i className="bi bi-check icon" />
                    Cancel anytime
                  </li>
                </ul>

                <div className="buttons">
                  <a
                    href={`/dashboard/${guildId}/premium`}
                    className="btn btn-premium"
                  >
                    Upgrade
                  </a>
                  <button
                    className="btn"
                    style={{ "--bs-btn-color": "#fff" } as React.CSSProperties}
                    data-bs-dismiss="modal"
                  >
                    Not now
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <style>{`
    #PremiumModal.modal.dark .btn-close {
      background-size: 50%;
      padding: 4px;
      background:
        transparent
        url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%23FFF'%3e%3cpath d='M.293.293a1 1 0 0 1 1.414 0L8 6.586 14.293.293a1 1 0 1 1 1.414 1.414L9.414 8l6.293 6.293a1 1 0 0 1-1.414 1.414L8 9.414l-6.293 6.293a1 1 0 0 1-1.414-1.414L6.586 8 .293 1.707a1 1 0 0 1 0-1.414z'/%3e%3c/svg%3e")
        center/1em
        auto
        no-repeat !important
    }

    .bg-img {
      height: 320px;
      width: 450px;
      margin-right: 16px;

      background-image: url('/legacy/img/bobcat1.png');
      background-size: cover;
      background-repeat: no-repeat;
      border-radius: 8px;
    }

    .icon {
      display: flex;
      font-size: 36px;
      color: green;
    }

    @media (min-width: 768px) {
      #PremiumModal .modal-dialog {
        --bs-modal-width: 70%;
      }
    }
    @media (min-width: 1024px) {
      #PremiumModal .modal-dialog {
        --bs-modal-width: 60%;
      }
    }
    @media (min-width: 1440px) {
      #PremiumModal .modal-dialog {
        --bs-modal-width: 50%;
      }
    }
`}</style>
    </div>
  );
}
