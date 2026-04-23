export const metadata = {
  title: "AI Council",
  description: "AI Council frontend"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}