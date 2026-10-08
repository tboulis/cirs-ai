import { formatDistanceToNow, parseISO } from "date-fns";
import { formatInTimeZone } from "date-fns-tz";

export const useDateFormatting = () => {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;

  const distanceToNow = (stringDate: string): string => {
    const isoRaw = stringDate.replace(" ", "T");
    const isoUtc = isoRaw.endsWith("Z") ? isoRaw : `${isoRaw}Z`;

    const date = parseISO(isoUtc);
    const localDate = formatInTimeZone(date, tz, "yyyy-MM-dd HH:mm:ss");
    return formatDistanceToNow(new Date(localDate), {
      addSuffix: true,
    });
  };

  return {
    distanceToNow,
  };
};
