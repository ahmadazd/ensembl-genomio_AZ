// See the NOTICE file distributed with this work for additional information
// regarding copyright ownership.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

include { DUMP_SEQ_REGIONS } from '../modules/dump_seq_regions.nf'
include { DUMP_EVENTS } from '../modules/dump_events.nf'
include { CHECK_JSON_SCHEMA } from '../modules/check_json_schema.nf'

include { COLLECT_FILES } from '../modules/collect_files.nf'
include { MANIFEST } from '../modules/collect_files.nf'
include { PUBLISH_DIR } from '../modules/collect_files.nf'

workflow DUMP_METADATA {
    take:
        server
        db
        filter_map
        out_dir

    emit:
        db

    main:
        seq_regions = DUMP_SEQ_REGIONS(server, db, filter_map)
        events = DUMP_EVENTS(server, db, filter_map)

        // Check files
        jsons_checked = CHECK_JSON_SCHEMA(seq_regions)

        // Collect all
        all_files = jsons_checked
            .concat(events)
            .map{ it[1] }
            .collate(5)
            .view()
        collect_dir = COLLECT_FILES(all_files, db)
        manifested_dir = MANIFEST(collect_dir, db)
        PUBLISH_DIR(manifested_dir, db, out_dir)
}
