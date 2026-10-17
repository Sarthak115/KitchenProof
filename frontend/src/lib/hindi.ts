// Hindi versions of the owner prompts, read aloud and shown under the English caption.
// Check IDs mirror backend/app/checks.py.
import type { Instruction } from './types'

const CHECKS_HI: Record<string, string> = {
  pests: 'स्टोव के नीचे का फ़र्श और कमरे के कोने दिखाइए',
  fridge_segregation: 'फ्रिज खोलिए और हर शेल्फ़ धीरे-धीरे दिखाइए',
  fridge_temp: 'कैमरा फ्रिज के थर्मामीटर के पास लाइए',
  handwash: 'हाथ धोने का सिंक दिखाइए और नल चालू कीजिए',
  handler_hygiene: 'खाना बनाने वाले व्यक्ति को कंधों से नीचे तक दिखाइए',
  order_prep: 'ऑर्डर #{orderId} अभी बनते हुए दिखाइए',
  dustbins: 'अपने डस्टबिन ढक्कन के साथ दिखाइए',
  surfaces: 'कटिंग बोर्ड और मुख्य कुकिंग काउंटर दिखाइए',
  drains: 'फ़र्श की नाली दिखाइए',
  dry_storage: 'आटा, चावल और सब्ज़ियाँ रखने की जगह दिखाइए',
  labels_expiry: 'दो पैकेट वाली सामग्री के लेबल दिखाइए',
  oil_condition: 'कढ़ाई या फ्रायर में तलने का तेल दिखाइए',
  walls_ceiling: 'खाना बनाने की जगह के ऊपर की दीवारें और छत धीरे-धीरे दिखाइए',
  fssai_board: 'दीवार पर लगा अपना FSSAI लाइसेंस दिखाइए',
  pest_control_record: 'अपना पिछला पेस्ट कंट्रोल सर्टिफ़िकेट दिखाइए',
  water_source: 'पीने के पानी का फ़िल्टर या स्रोत दिखाइए',
}

const OBJECTS_HI: Record<string, string> = {
  stove: 'स्टोव',
  fridge: 'फ्रिज',
  sink: 'सिंक',
  'gas cylinder': 'गैस सिलेंडर',
}

/** Hindi text for an instruction, or null if it can't be translated. */
export function hindiPrompt(i: Instruction): string | null {
  if (i.kind === 'liveness') {
    const m = i.prompt.match(/Hold up (\d) fingers? in front of the (.+)$/)
    if (!m || !OBJECTS_HI[m[2]]) return null
    return `${OBJECTS_HI[m[2]]} के सामने ${m[1]} ${m[1] === '1' ? 'उंगली' : 'उंगलियाँ'} दिखाइए`
  }
  const text = i.checkId ? CHECKS_HI[i.checkId] : undefined
  if (!text) return null
  const order = i.prompt.match(/#(\S+)/)?.[1] ?? ''
  return text.replace('{orderId}', order)
}
