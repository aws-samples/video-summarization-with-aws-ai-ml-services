import React from "react";
import SideNavigation, {
  SideNavigationProps,
} from "@cloudscape-design/components/side-navigation";

const items: SideNavigationProps["items"] = [
  { type: "link", text: "Home", href: "/" },
  { type: "link", text: "Dashboard", href: "/vsh" },
];

export default function Navigation() {
  return (
    <>
      <SideNavigation
        activeHref={location.pathname}
        header={{ href: "/", text: "Internal Tooling" }}
        items={items}
      />
    </>
  );
}
