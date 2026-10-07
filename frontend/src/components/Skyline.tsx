/** Collegiate Gothic skyline (adapted from the HW4 Campus Customs site), drawn in SVG. */
export default function Skyline() {
  return (
    <svg className="skyline" viewBox="0 0 1200 160" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <g fill="#ffffff" fillOpacity="0.09">
        <circle cx="40" cy="125" r="34" />
        <circle cx="85" cy="112" r="40" />
        <circle cx="130" cy="130" r="30" />
        <path d="M150 160V90l40-26 40 26V74h120v16l40-26 40 26v70z" />
        <path d="M455 160V82h18l9-44 9 44h18v78z" />
        <path d="M560 160V70h12V40h10V22h8V8l10-12 10 12v14h8v18h10v30h12v90z" />
        <path d="M660 160v-58h230v58z" />
        <path d="M900 160V78h14V56l14-18 14 18v22h14v82z" />
        <path d="M970 160v-60l30-22 30 22 30-22 30 22v60z" />
        <circle cx="1120" cy="122" r="38" />
        <circle cx="1170" cy="134" r="30" />
      </g>
      <g fill="#00264d" fillOpacity="0.45">
        {[680, 725, 770, 815, 860].map((x) => (
          <path key={x} d={`M${x} 160v-30a12 12 0 0 1 24 0v30z`} />
        ))}
        <circle cx="600" cy="84" r="8" />
      </g>
    </svg>
  )
}
