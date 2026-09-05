/** Port of templates/components/plugin_disabled_modal.html.
 *  Behaviour lives in /legacy/dash/js/main.js -> window.PluginDisabledModal. */
export function PluginDisabledModal({ guildId }: { guildId: string }) {
  return (
    <div
      id="PluginDisabledModal"
      className="modal dark"
      tabIndex={-1}
      data-guild-id={guildId}
    >
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

            <h5 className="m-0">This plugin is turned off</h5>
            <p className="mt-2 mb-3" style={{ color: "#899bbd" }}>
              <span className="pdm-plugin-name">This plugin</span> is currently
              disabled. Activate it to open and configure it.
            </p>

            <div className="buttons d-flex justify-content-end gap-2">
              <button
                id="pdm-cancel"
                className="btn"
                style={{ "--bs-btn-color": "#fff" } as React.CSSProperties}
                data-bs-dismiss="modal"
              >
                Cancel
              </button>
              <button id="pdm-activate" className="btn btn-blurple">
                Activate <span className="pdm-plugin-name">this plugin</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
