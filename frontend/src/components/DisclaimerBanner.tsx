/**
 * Disclaimer Banner Component
 * 
 * Prominently displays the legal and ethical disclaimers.
 * This is NOT a mixer or obfuscation service.
 */

function DisclaimerBanner() {
  return (
    <div className="disclaimer-banner">
      <h3>⚠️ Important Disclaimers</h3>
      <ul>
        <li>This is NOT a mixer, tumbler, or obfuscation service</li>
        <li>This does NOT provide "untraceable" or "anonymous" transfers</li>
        <li>All behavior is explainable, auditable, and user-approved</li>
        <li>Default mode is SIMULATION ONLY - execution requires explicit confirmation</li>
        <li>This tool enforces OPERATIONAL DISCIPLINE, not fantasy anonymity</li>
      </ul>
    </div>
  );
}

export default DisclaimerBanner;
