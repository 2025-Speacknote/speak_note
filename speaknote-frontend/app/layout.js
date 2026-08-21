import "./globals.css";

export const metadata = {
  title: "SpeakNote Queue Tester",
  description: "MAX_PROCESS_NUM batch flush and coroutine latency tester",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
