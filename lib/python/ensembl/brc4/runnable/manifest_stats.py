#!env python3
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from collections import Counter
import gzip
import io
from pathlib import Path
from statistics import mean
from typing import Dict, List, TextIO

from BCBio import GFF
import eHive

from ensembl.brc4.runnable.utils import get_json


class manifest_stats(eHive.BaseRunnable):

    def run(self):
        manifest_path = Path(self.param_required("manifest"))
        manifest = self.get_manifest(manifest_path)
        
        stats = []
        if "gff3" in manifest:
            stats += self.get_gff3_stats(Path(manifest["gff3"]))
        if "seq_region" in manifest:
            stats += self.get_seq_region_stats(Path(manifest["seq_region"]))
        
        stats_path = manifest_path.parent / "stats.txt"
        print(stats_path)
        with stats_path.open("w") as stats_out:
            stats_out.write("\n".join(stats))
        
    def get_manifest(self, manifest_path: Path) -> Dict:
        manifest = get_json(manifest_path)
        manifest_root = manifest_path.parent
        
        # Use dir name from the manifest
        for name in manifest:
            if "file" in manifest[name]:
                file_name = manifest[name]["file"]
                file_name = manifest_root / file_name
                manifest[name] = file_name
            else:
                for f in manifest[name]:
                    if "file" in manifest[name][f]:
                        file_name = manifest[name][f]["file"]
                        file_name = manifest_root, file_name
                        manifest[name][f] = file_name
        
        return manifest

    def get_seq_region_stats(self, seq_region_path: Path) -> List:
        
        seq_regions = get_json(seq_region_path)
        
        # Get basic data
        coord_systems = {}
        circular = 0
        locations = []
        codon_tables = []
        for seqr in seq_regions:
            # Get readable seq_region name
            genbank = "synonyms" in seqr and [x for x in seqr["synonyms"] if x["source"] == "GenBank"]
            seqr_name = genbank and genbank[0]["name"] or seqr["name"]

            coord_level = seqr["coord_system_level"]
            if not coord_level in coord_systems:
                coord_systems[coord_level] = []
            coord_systems[coord_level].append(seqr["length"])
            
            if "circular" in seqr:
                circular += 1
            if "codon_table" in seqr:
                codon_tables.append("%s = %s" % (seqr_name, seqr["codon_table"]))
            if "location" in seqr:
                locations.append("%s = %s" % (seqr_name, seqr["location"]))
        
        # Stats
        stats = []
        stats.append(seq_region_path.name)
        stats.append("Total coord_systems %d" % len(coord_systems))
        for coord_name, lengths in coord_systems.items():
            stats.append("\nCoord_system: %s" % coord_name)
            
            stat_counts = dict()
            stat_counts["Number of sequences"] = len(lengths)
            stat_counts["Sequence length sum"] = sum(lengths)
            stat_counts["Sequence length minimum"] = min(lengths)
            stat_counts["Sequence length mean"] = mean(lengths)
            stat_counts["Sequence length maximum"] = max(lengths)

            for name, count in stat_counts.items():
                stats.append("%9d\t%s" % (count, name))
        
        # Special
        if circular or locations:
            stats.append("\nSpecial")
            if circular:
                stats.append("%9d\t%s" % (circular, "circular sequences"))
            if locations:
                stats.append("%9d\t%s" % (len(locations), "sequences with location"))
                for loc in locations:
                    stats.append("\t\t\t%s" % loc)
            if codon_tables:
                stats.append("%9d\t%s" % (len(codon_tables), "sequences with codon_table"))
                for table in codon_tables:
                    stats.append("\t\t\t%s" % table)
        
        stats.append("\n")

        return stats

    def get_gff3_stats(self, gff3_path: Path) -> List:
        
        stats = []
        stats.append(gff3_path.name)
        if gff3_path.name.endswith(".gz"):
            with io.TextIOWrapper(gzip.open(gff3_path, "r")) as gff3_handle:
                stats += self.parse_gff3(gff3_handle)
        else:
            with gff3_path.open("r") as gff3_handle:
                stats += self.parse_gff3(gff3_handle)
        stats.append("\n")
        
        return stats

    def parse_gff3(self, gff3_handle: TextIO) -> List:
        biotypes = {}

        for rec in GFF.parse(gff3_handle):
            for feat1 in rec.features:
                is_protein = False
                for feat2 in feat1.sub_features:
                    if feat2.type == "mRNA":
                        is_protein = True
                    manifest_stats.increment_biotype(biotypes, feat2.id,  f"{feat1.type}-{feat2.type}")
                    for feat3 in feat2.sub_features:
                        if feat3.type == 'exon':
                            continue
                        manifest_stats.increment_biotype(biotypes, feat3.id, f"{feat1.type}-{feat2.type}-{feat3.type}")
                if is_protein:
                    manifest_stats.increment_biotype(biotypes, feat1.id, f"PROT_{feat1.type}")
                else:
                    manifest_stats.increment_biotype(biotypes, feat1.id, f"NONPROT_{feat1.type}")
                
                if feat1.type in ("gene", "pseudogene"):
                    manifest_stats.increment_biotype(biotypes, feat1.id, "ALL_GENES")
                
        # Order
        sorted_biotypes = dict()
        for name in sorted(biotypes.keys()):
            data = biotypes[name]
            counter = Counter(data["ids"])
            data["unique_count"] = len(counter.keys())
            sorted_biotypes[name] = data
        
        stats = [f"{data['unique_count']:>9}\t{biotype:<20}\tID = {data['example']}" for (biotype, data) in sorted_biotypes.items()]
        
        return stats

    @staticmethod
    def increment_biotype(biotypes: Dict, feature_id: str, feature_biotype: str) -> None:
        if not feature_biotype in biotypes:
            biotypes[feature_biotype] = { "count" : 0, "ids": [], "example" : feature_id }
        biotypes[feature_biotype]["count"] += 1
        # Only count IDs once!
        biotypes[feature_biotype]["ids"].append(feature_id)
        
