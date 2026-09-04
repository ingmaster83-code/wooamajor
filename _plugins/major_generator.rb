require 'json'

module Jekyll
  class MajorPageGenerator < Generator
    safe true
    priority :normal

    SCHOOL_MAJOR_CAP = 500  # 학교 페이지당 서버사이드 렌더링 상한(대형 학교 대응)

    def generate(site)
      raw_dir = File.join(site.source, '_rawdata')
      shard_files = Dir.glob(File.join(raw_dir, 'schools_*.json'))

      total_schools = 0
      total_sigungu = 0

      shard_files.each do |path|
        do_short = File.basename(path, '.json').sub('schools_', '')
        schools = load_json(path)
        next if schools.empty?

        by_sigungu = schools.group_by { |s| s['sigungu'].to_s.strip }
        by_sigungu.delete('')

        site.pages << DoIndexPage.new(site, do_short, schools.size, by_sigungu)
        total_sigungu += by_sigungu.size

        by_sigungu.each do |sigungu, sg_schools|
          site.pages << SigunguPage.new(site, do_short, sigungu, sg_schools)

          sg_schools.each do |school|
            site.pages << SchoolPage.new(site, do_short, sigungu, school)
            total_schools += 1
          end
        end
      end

      Jekyll.logger.info "MajorGenerator:", "완료 (시도 #{shard_files.size}개 + 시군구 #{total_sigungu}개 + 학교 #{total_schools}개)"
    end

    private

    def load_json(path)
      return [] unless File.exist?(path)
      JSON.parse(File.read(path, encoding: 'utf-8'))
    rescue => e
      Jekyll.logger.warn "MajorGenerator:", "#{path} 로드 실패: #{e.message}"
      []
    end
  end

  class DoIndexPage < Page
    def initialize(site, do_short, total_count, by_sigungu)
      @site = site
      @base = site.source
      @dir  = "region/#{do_short}"
      @name = 'index.html'

      sigungu_list = by_sigungu.map { |sg, list| { 'name' => sg, 'count' => list.size } }
                               .sort_by { |h| -h['count'] }

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'do.html')
      self.data['doShort']     = do_short
      self.data['totalCount']  = total_count
      self.data['sigunguList'] = sigungu_list
      self.data['layout']      = 'do'
      self.data['title']       = "#{do_short} 대학교 학과정보 #{total_count}개교"
      self.data['description'] = "#{do_short} 지역 대학교·전문대학 #{total_count}개교의 학과 정보를 시군구별로 확인하세요."[0, 155]
    end
  end

  class SigunguPage < Page
    def initialize(site, do_short, sigungu, schools)
      @site = site
      @base = site.source
      @dir  = "region/#{do_short}/#{sigungu}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'sigungu.html')
      self.data['doShort']    = do_short
      self.data['sigungu']    = sigungu
      self.data['totalCount'] = schools.size
      self.data['schools']    = schools.sort_by { |s| -s['majorCount'] }
      self.data['layout']     = 'sigungu'
      self.data['title']      = "#{do_short} #{sigungu} 대학교 학과정보 #{schools.size}개교"
      self.data['description'] = "#{do_short} #{sigungu}의 대학교·전문대학 #{schools.size}개교 학과 정보를 확인하세요."[0, 155]
    end
  end

  class SchoolPage < Page
    def initialize(site, do_short, sigungu, school)
      @site = site
      @base = site.source
      @dir  = "school/#{school['slug']}"
      @name = 'index.html'

      majors = school['majors'] || []
      capped = majors.first(MajorPageGenerator::SCHOOL_MAJOR_CAP)

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'school.html')
      self.data['doShort']      = do_short
      self.data['sigungu']      = sigungu
      self.data['schoolName']   = school['schoolName']
      self.data['schoolType']   = school['schoolType']
      self.data['majorCount']   = school['majorCount']
      self.data['affils']       = school['affils']
      self.data['degrees']      = school['degrees']
      self.data['majors']       = capped
      self.data['truncated']    = majors.size > MajorPageGenerator::SCHOOL_MAJOR_CAP
      self.data['layout']       = 'school'
      self.data['title']        = "#{school['schoolName']} 학과정보 · 입학정원 · 관련직업"
      self.data['description']  = "#{school['schoolName']}의 학과 #{school['majorCount']}개(학위과정·모집정원·졸업자수·관련직업)를 한눈에 확인하세요."[0, 155]
    end
  end
end
