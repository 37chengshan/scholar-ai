import { useLanguage } from '../contexts/LanguageContext';
import { Label } from './ui/label';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';

interface FontSizeSelectorProps {
  value: 'small' | 'medium' | 'large' | 'extra-large';
  onChange: (size: 'small' | 'medium' | 'large' | 'extra-large') => void;
}

/**
 * FontSizeSelector Component
 *
 * Radio Group for selecting font size (D-10).
 * Four options: Small (14px), Medium (16px), Large (18px), Extra Large (20px)
 *
 * Applies to body text only, not headings.
 */
export function FontSizeSelector({ value, onChange }: FontSizeSelectorProps) {
  const { language } = useLanguage();
  const isZh = language === "zh";

  const t = {
    title: isZh ? "字体大小" : "Font Size",
    small: isZh ? "小" : "Small",
    smallDesc: "14px",
    medium: isZh ? "中" : "Medium",
    mediumDesc: "16px",
    large: isZh ? "大" : "Large",
    largeDesc: "18px",
    extraLarge: isZh ? "特大" : "Extra Large",
    extraLargeDesc: "20px",
  };

  const options: Array<{
    value: 'small' | 'medium' | 'large' | 'extra-large';
    label: string;
    desc: string;
  }> = [
    { value: 'small', label: t.small, desc: t.smallDesc },
    { value: 'medium', label: t.medium, desc: t.mediumDesc },
    { value: 'large', label: t.large, desc: t.largeDesc },
    { value: 'extra-large', label: t.extraLarge, desc: t.extraLargeDesc },
  ];

  return (
    <div className="space-y-3">
      <Label className="text-sm font-semibold">{t.title}</Label>
      <RadioGroup
        value={value}
        onValueChange={(val) => onChange(val as typeof value)}
        className="grid grid-cols-2 gap-3"
      >
        {options.map((option) => (
          <div
            key={option.value}
            className="flex items-center space-x-2 p-3 border border-[#f4ece1] rounded-sm hover:border-[#d35400] transition-colors cursor-pointer"
          >
            <RadioGroupItem value={option.value} id={option.value} />
            <div className="flex-1">
              <Label
                htmlFor={option.value}
                className="text-sm font-semibold cursor-pointer"
              >
                {option.label}
              </Label>
              <p className="text-xs text-muted-foreground">{option.desc}</p>
            </div>
          </div>
        ))}
      </RadioGroup>
    </div>
  );
}