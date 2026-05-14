import { keyframes } from "@mui/system";

export const decisionGlow = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.0); }
  20% { box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.30); }
  100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.0); }
`;

export const decisionFadeIn = keyframes`
  0% { opacity: 0; transform: translateY(2px); }
  100% { opacity: 1; transform: translateY(0); }
`;

export const chipPop = keyframes`
  0% { transform: scale(0.96); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
`;
