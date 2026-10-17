# SPDX-License-Identifier: Apache-2.0
"""Normalize equivalent wording while preserving meaningful design differences."""
import re
ALIASES={
    "neckline":{"square neck":"square","crew neck":"crew","crewneck":"crew","v neck":"v-neck","vneck":"v-neck","scoop neck":"scoop","halter neck":"halter","high neck":"high neck"},
    "sleeve_length":{"short sleeves":"short","short sleeve":"short","long sleeves":"long","long sleeve":"long","3/4 sleeves":"three quarter","three quarter sleeves":"three quarter"},
    "sleeve_shape":{"puff sleeves":"puff","puffed sleeves":"puff","puffed":"puff","plain sleeves":"plain","bell sleeves":"bell","balloon sleeves":"balloon","cap sleeves":"cap","raglan sleeves":"raglan"},
    "length":{"cropped length":"cropped","mini length":"mini","midi length":"midi","maxi length":"maxi","hip":"hip length"},
    "hem":{"straight hem":"straight","asymmetric hem":"asymmetric","scalloped hem":"scalloped","ruffle hem":"ruffled","ruffled hem":"ruffled","split hem":"split"},
    "closure":{"buttons":"button","zipper":"zip"},
    "pattern":{"plain solid":"plain","solid":"plain","solid colour":"plain","floral print":"floral","geometric print":"geometric","graphic print":"graphic","polka dots":"polka dot","gingham check":"gingham","plaid check":"plaid","leopard print":"leopard"},
    "colour":{"navy blue":"navy","gray":"grey"},
    "silhouette":{"a line":"a-line"},
}
def normalise_values(key,values):
    out=[]
    for value in values:
        parts=re.split(r"[,/]",str(value)) if key=="colour" else [str(value)]
        for part in parts:
            text=re.sub(r"\s+"," ",part.strip().casefold().replace("-"," "))
            text=ALIASES.get(key,{}).get(text,text)
            if text:out.append(text)
    return sorted(set(out))

