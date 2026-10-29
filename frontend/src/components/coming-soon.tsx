import Link from "next/link";
import { Icon, type IconName } from "./icons";
import { btnSecondary, card } from "./ui";

export function ComingSoon({ title, icon, text }: { title: string; icon: IconName; text: string }) {
  return (
    <div className="mx-auto max-w-[1200px] px-5 py-8 sm:px-8">
      <h1 className="text-2xl font-semibold text-gray-800 dark:text-white/90">{title}</h1>
      <div className={`${card} mt-8 flex flex-col items-center px-6 py-14 text-center`}>
        <span className="inline-flex size-12 items-center justify-center rounded-full bg-primary-50 text-primary-500 dark:bg-primary-500/15">
          <Icon name={icon} className="size-6" />
        </span>
        <p className="mt-4 text-base font-semibold text-gray-800 dark:text-white/90">Coming in the next sprint</p>
        <p className="mt-2 max-w-md text-sm text-gray-500 dark:text-gray-400">{text}</p>
        <Link href="/projects" className={`${btnSecondary} mt-6`}>
          Back to my projects
        </Link>
      </div>
    </div>
  );
}
