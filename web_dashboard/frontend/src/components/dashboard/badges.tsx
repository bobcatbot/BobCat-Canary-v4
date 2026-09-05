/** Ports of templates/components/badges/*.html */

const SparkSvg = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
    <g>
      <rect fill="none" height="24" width="24" x="0" />
    </g>
    <g>
      <g>
        <polygon points="19,9 20.25,6.25 23,5 20.25,3.75 19,1 17.75,3.75 15,5 17.75,6.25" />
        <polygon points="19,15 17.75,17.75 15,19 17.75,20.25 19,23 20.25,20.25 23,19 20.25,17.75" />
        <path d="M11.5,9.5L9,4L6.5,9.5L1,12l5.5,2.5L9,20l2.5-5.5L17,12L11.5,9.5z M9.99,12.99L9,15.17l-0.99-2.18L5.83,12l2.18-0.99 L9,8.83l0.99,2.18L12.17,12L9.99,12.99z" />
      </g>
    </g>
  </svg>
);

export const BadgeNew = () => (
  <div className="badge rounded-pill badge-green">
    <SparkSvg /> New
  </div>
);

export const BadgeBeta = () => (
  <div className="badge rounded-pill badge-orange">
    <SparkSvg /> Beta
  </div>
);

export const BadgeSoon = () => (
  <div className="badge rounded-pill badge-gray">
    <SparkSvg /> Soon
  </div>
);

export const BadgePrem = () => (
  <div className="badge rounded-pill badge-orange prem">
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      fill="currentColor"
      className="bi bi-star-fill"
      viewBox="0 0 16 16"
    >
      <path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 13.187l-4.389 2.256z" />
    </svg>
  </div>
);

/** Sidebar badge selection — mirrors the {% if plugin.badge %} chain. */
export function SidebarBadge({
  badge,
  premium,
  guildPremium,
}: {
  badge: string;
  premium: boolean;
  guildPremium: boolean;
}) {
  if (badge === "new") return <BadgeNew />;
  if (badge === "beta") return <BadgeBeta />;
  if (badge === "soon") return <BadgeSoon />;
  if (badge === "prem" && premium && !guildPremium) return <BadgePrem />;
  return null;
}
