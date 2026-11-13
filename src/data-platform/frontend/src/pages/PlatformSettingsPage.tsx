import { Banner, Panel } from "@retail-lakehouse/design-system";
import { useGetPlatformSettings } from "@/api/generated/platform-settings/platform-settings";
import type { PlatformSettingApiResponse, PlatformSettingsGroupApiResponse } from "@/api/generated/model";
import { PageHeader } from "@/components/PageHeader";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { errorMessage } from "@/format";
import { platformSettingText } from "@/lib/platformSettingText";

function Fact({ item }: { item: PlatformSettingApiResponse }) {
  const { value, exact } = platformSettingText(item);
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t border-outline py-3 first:border-t-0 first:pt-0 last:pb-0">
      <dt>{item.label}</dt>
      <dd className="flex flex-wrap items-baseline gap-x-2">
        <span className="font-mono tabular-nums">{value}</span>
        {exact !== null && (
          <span className="font-mono tabular-nums type-body-small text-on-surface-variant">{exact}</span>
        )}
      </dd>
      <dd className="type-body-small basis-full text-on-surface-variant">{item.description}</dd>
    </div>
  );
}

// A panel takes focus because the page has nothing else to focus: a keyboard reader scrolls the page
// from one group to the next.
function GroupPanel({ group }: { group: PlatformSettingsGroupApiResponse }) {
  return (
    <Panel
      title={group.title}
      tabIndex={0}
      className="focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring"
    >
      <dl>
        {group.items.map((item) => (
          <Fact key={item.key} item={item} />
        ))}
      </dl>
    </Panel>
  );
}

// The settings the platform runs with, in groups; the deployment sets them, so the page only reads them.
export function PlatformSettingsPage() {
  const settings = useGetPlatformSettings();
  return (
    <section>
      <PageHeader title="Platform settings">
        <span>These values are set by the platform deployment; the console cannot change them.</span>
      </PageHeader>
      {settings.isError && (
        <Banner type="negative" title={`Could not load platform settings: ${errorMessage(settings.error)}`} />
      )}
      {settings.isPending && <PanelSkeleton label="Loading platform settings" />}
      {settings.data !== undefined && (
        <div className="flex flex-col gap-4">
          {settings.data.groups.map((group) => (
            <GroupPanel key={group.key} group={group} />
          ))}
        </div>
      )}
    </section>
  );
}
